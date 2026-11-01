"""Menyusun laporan dari sebuah Sumber dengan Gemini: teks, gambar, dan video dikirim sekaligus (multimodal)."""

from __future__ import annotations

import json
import re
import time
from datetime import date

from google import genai
from google.genai import types

from .schema import LIST_FIELDS, TIDAK_ADA, LaporanBerita
from .sources import Sumber

BULAN = ["Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli", "Agustus",
         "September", "Oktober", "November", "Desember"]

PROMPT = f"""Anda adalah analis media yang menyusun laporan ringkas pemberitaan untuk {{wilayah}}.
Telaah sumber berita terlampir (teks, gambar, dan/atau video) lalu susun laporan yang padat, lugas, dan objektif.

ATURAN WAJIB:
1. Gunakan HANYA informasi yang benar-benar ada di sumber. Jangan mengarang nama orang, kelompok, angka,
   tanggal, atau lokasi.
2. Bila suatu bagian tidak ada di sumber, tulis "{TIDAK_ADA}". Untuk bagian berbentuk daftar, isi satu butir
   "{TIDAK_ADA}".
3. Dampak, risiko, dan rekomendasi boleh berupa penilaian, tetapi harus berangkat dari fakta di sumber.
4. Jangan menulis nomor atau simbol bullet (-, a., 1.) di dalam butir daftar; penomoran diatur sistem.
5. Isi "ringkasan_sumber" dengan fakta dari sumber saja, supaya pembaca bisa memeriksa laporan.
"""

def tanggal_surat(today: date | None = None) -> str:
    d = today or date.today()
    return f"{BULAN[d.month - 1]} {d.year}"


def bersihkan_butir(items: list[str]) -> list[str]:
    out = []
    for item in items:
        clean = re.sub(r"^\s*(?:[a-zA-Z0-9]{1,3}[.)]|[•\-*])\s*", "", item).strip()
        if clean:
            out.append(clean)
    return out or [TIDAK_ADA]


def susun_parts(sumber: Sumber, wilayah: str, pakai_video: bool = True) -> list[types.Part]:
    header = (f"{PROMPT.format(wilayah=wilayah)}\n--- SUMBER ({sumber.jenis.upper()}) ---\n"
              f"Tautan: {sumber.url}\n{sumber.teks or '(tidak ada teks; baca dari gambar/video)'}")
    parts = [types.Part(text=header)]
    for g in sumber.gambar:
        parts.append(types.Part.from_bytes(data=g.data, mime_type=g.mime_type))
    if pakai_video and sumber.video_uri:
        parts.append(types.Part(file_data=types.FileData(file_uri=sumber.video_uri)))
    return parts


def _kode(err: Exception) -> str:
    msg = str(err)
    for code in ("429", "503", "404", "400", "403"):
        if code in msg:
            return code
    if "UNAVAILABLE" in msg or "RESOURCE_EXHAUSTED" in msg:
        return "503"
    if "NOT_FOUND" in msg:
        return "404"
    return ""


class VideoDitolak(Exception):
    """Gemini menolak membaca video (privat, dibatasi umur, atau terlalu panjang)."""


class Analis:
    def __init__(self, client: genai.Client, models: list[str], wilayah: str, sleep=time.sleep):
        self.client, self.models, self.wilayah, self.sleep = client, models, wilayah, sleep

    def _panggil(self, model: str, parts: list[types.Part], video: bool) -> dict:
        config = types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=LaporanBerita,
            temperature=0.2,
            # Resolusi rendah untuk video: token jauh lebih hemat, cukup untuk memahami isi berita.
            media_resolution=types.MediaResolution.MEDIA_RESOLUTION_LOW if video else None,
        )
        resp = self.client.models.generate_content(
            model=model, contents=[types.Content(role="user", parts=parts)], config=config)
        return json.loads(resp.text)

    def analisis(self, sumber: Sumber) -> dict:
        try:
            return self._coba_semua_model(sumber, pakai_video=bool(sumber.video_uri))
        except VideoDitolak:
            # Video tidak bisa dibaca: ulangi dengan judul/teks saja, dan beri tahu pengguna.
            sumber.catatan.append("Video tidak bisa dibaca Gemini (privat, dibatasi, atau terlalu panjang); "
                                  "laporan disusun dari judul saja, periksa dengan teliti.")
            return self._coba_semua_model(sumber, pakai_video=False)

    def _coba_semua_model(self, sumber: Sumber, pakai_video: bool) -> dict:
        parts = susun_parts(sumber, self.wilayah, pakai_video)
        last: Exception | None = None
        for model in self.models:
            for attempt in range(2):
                try:
                    return self._rapikan(self._panggil(model, parts, pakai_video))
                except Exception as e:  # noqa: BLE001 - error API Gemini berbentuk bermacam-macam
                    last, kode = e, _kode(e)
                    if kode in ("429", "503"):  # sibuk atau kuota: tunggu sebentar, coba lagi
                        self.sleep(2 * (attempt + 1))
                        continue
                    if kode == "404":  # model tidak tersedia: lanjut ke model berikutnya
                        break
                    if kode in ("400", "403") and pakai_video:
                        raise VideoDitolak() from e
                    raise
        raise RuntimeError(f"Semua model Gemini gagal atau sibuk. Error terakhir: {last}")

    def _rapikan(self, data: dict) -> dict:
        for name in LIST_FIELDS:
            data[name] = bersihkan_butir(data.get(name) or [])
        data["tanggal_surat"] = tanggal_surat()  # dari kalender, bukan tebakan model
        data["wilayah"] = self.wilayah
        return data
