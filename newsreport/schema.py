"""Isi laporan yang harus dikembalikan Gemini (structured output)."""

from __future__ import annotations

from pydantic import BaseModel, Field

TIDAK_ADA = "Tidak disebutkan dalam sumber"


class LaporanBerita(BaseModel):
    # Diisi paling awal, supaya model merangkum isi sumber dulu sebelum menilai.
    ringkasan_sumber: str = Field(description=(
        "Ringkasan faktual isi berita dari sumber: siapa, apa, di mana, kapan. Hanya fakta yang benar-benar "
        "ada di sumber (teks, gambar, atau video). Dipakai pembaca untuk memeriksa laporan."))
    judul_laporan: str = Field(description="Judul laporan huruf kapital, singkat, sesuai isu utama berita")
    latar_belakang: str = Field(description="Satu paragraf konteks: isu apa dan mengapa muncul")
    pokok_peristiwa: list[str] = Field(description="3-5 fakta utama peristiwa, tanpa awalan angka/huruf")
    pihak_terkait: list[str] = Field(description="Orang, lembaga, atau kelompok yang disebut di sumber")
    lokasi: list[str] = Field(description="Lokasi yang disebut di sumber")
    waktu: str = Field(description="Waktu atau periode peristiwa menurut sumber")
    sentimen_publik: str = Field(description="Kecenderungan sikap publik/media terhadap isu, dari sumber")
    dampak: list[str] = Field(description="2-4 dampak yang sudah atau mungkin terjadi, tanpa awalan angka/huruf")
    potensi_risiko: list[str] = Field(description="2-4 risiko bila isu berkembang, tanpa awalan angka/huruf")
    rekomendasi: list[str] = Field(description="3-5 langkah yang disarankan, tanpa awalan angka/huruf")


LIST_FIELDS = [name for name, f in LaporanBerita.model_fields.items() if f.annotation == list[str]]
