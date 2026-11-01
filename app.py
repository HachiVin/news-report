"""News-to-Report Generator: tempel link berita (web, Instagram, TikTok, YouTube), dapatkan draf laporan Word.

    streamlit run app.py
"""

from __future__ import annotations

import io
import os
import zipfile

import streamlit as st
from google import genai

from newsreport import config
from newsreport.analyzer import Analis
from newsreport.document import isi_template, nama_file, sisa_placeholder
from newsreport.schema import TIDAK_ADA
from newsreport.sources import ambil_sumber

st.set_page_config(page_title="News-to-Report Generator", page_icon="📄", layout="wide")
st.markdown("""
<style>
  .block-container{padding-top:2rem;max-width:1180px}
  .tag{display:inline-block;padding:2px 10px;border-radius:999px;font-size:.78rem;font-weight:600;
       border:1px solid rgba(128,128,128,.35);margin-right:6px}
  .src{color:#8a8a8a;font-size:.85rem;word-break:break-all}
</style>""", unsafe_allow_html=True)

JENIS_LABEL = {"web": "Web berita", "instagram": "Instagram", "tiktok": "TikTok", "youtube": "YouTube"}

# ---------- Sidebar: pengaturan dan penjelasan ----------
with st.sidebar:
    st.header("Pengaturan")
    template_upload = st.file_uploader("Template .docx (opsional)", type=["docx"],
                                       help="Kosongkan untuk memakai template.docx di folder aplikasi.")
    wilayah = st.text_input("Wilayah", value=config.WILAYAH)
    st.divider()
    st.subheader("Yang dibaca per link")
    st.markdown(
        "- **Web berita**: isi artikel lengkap\n"
        "- **Instagram**: caption dan gambar utama\n"
        "- **TikTok**: caption dan gambar sampul\n"
        "- **YouTube**: isi video (gambar dan suara)\n\n"
        f"Bagian yang tidak ada di sumber ditulis *{TIDAK_ADA}*, bukan dikarang.")
    st.caption("Model: " + ", ".join(config.GEMINI_MODELS))

st.title("News-to-Report Generator")
st.caption("Draf laporan ringkas pemberitaan dari link berita dan media sosial. "
           "Hasil adalah draf: periksa ringkasan sumber sebelum dokumen dipakai.")

if not config.GEMINI_API_KEY:
    st.error("GEMINI_API_KEY belum diisi. Salin `.env.example` menjadi `.env`, isi key-nya, lalu jalankan ulang.")
    st.stop()


def muat_template() -> bytes | None:
    if template_upload is not None:
        return template_upload.getvalue()
    if os.path.exists(config.TEMPLATE_PATH):
        with open(config.TEMPLATE_PATH, "rb") as f:
            return f.read()
    return None


# ---------- Input ----------
urls_text = st.text_area("Link berita atau media sosial, satu per baris", height=150, placeholder=(
    "https://news.detik.com/...\nhttps://www.instagram.com/p/...\n"
    "https://vt.tiktok.com/...\nhttps://www.youtube.com/watch?v=..."))
jalan = st.button("Proses dan buat laporan", type="primary")

if jalan:
    urls = [u.strip() for u in urls_text.splitlines() if u.strip()]
    template = muat_template()
    if not urls:
        st.warning("Masukkan minimal satu link.")
    elif template is None:
        st.error(f"Template tidak ditemukan. Letakkan `{config.TEMPLATE_PATH}` di folder aplikasi "
                 "atau unggah lewat sidebar.")
    else:
        analis = Analis(genai.Client(api_key=config.GEMINI_API_KEY), config.GEMINI_MODELS, wilayah)
        hasil = []
        with st.status(f"Memproses {len(urls)} link...", expanded=True) as status:
            for i, url in enumerate(urls, 1):
                st.write(f"{i}/{len(urls)} · {url[:80]}")
                try:
                    sumber = ambil_sumber(url)
                    data = analis.analisis(sumber)
                    berkas = isi_template(template, data)
                    hasil.append({"ok": True, "url": url, "sumber": sumber, "data": data, "docx": berkas,
                                  "sisa": sisa_placeholder(berkas)})
                except Exception as e:  # noqa: BLE001 - satu link gagal tidak menghentikan yang lain
                    hasil.append({"ok": False, "url": url, "error": str(e)})
            n_ok = sum(h["ok"] for h in hasil)
            status.update(label=f"Selesai: {n_ok} berhasil, {len(hasil) - n_ok} gagal", state="complete",
                          expanded=False)
        # Disimpan di session_state supaya hasil tidak hilang saat tombol unduh diklik (Streamlit menjalankan ulang skrip).
        st.session_state["hasil"] = hasil


def daftar(judul: str, items: list[str]) -> None:
    st.markdown(f"**{judul}**")
    st.markdown("\n".join(f"- {x}" for x in items) or f"- {TIDAK_ADA}")


# ---------- Hasil ----------
hasil = st.session_state.get("hasil", [])
if hasil:
    berhasil = [h for h in hasil if h["ok"]]
    st.subheader(f"Hasil ({len(berhasil)} dari {len(hasil)} link)")
    if len(berhasil) > 1:
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
            for i, h in enumerate(berhasil, 1):
                z.writestr(nama_file(h["data"]["judul_laporan"], i), h["docx"])
        st.download_button("Unduh semua (.zip)", buf.getvalue(), "Kumpulan_Laporan.zip", "application/zip")

    for i, h in enumerate(hasil, 1):
        if not h["ok"]:
            with st.container(border=True):
                st.markdown(f"**{i}. Gagal diproses**")
                st.markdown(f"<div class='src'>{h['url']}</div>", unsafe_allow_html=True)
                st.error(h["error"])
            continue
        s, d = h["sumber"], h["data"]
        with st.container(border=True):
            st.markdown(f"<span class='tag'>{JENIS_LABEL[s.jenis]}</span>"
                        f"<span class='tag'>dibaca: {', '.join(s.dibaca) or '-'}</span>", unsafe_allow_html=True)
            st.markdown(f"#### {i}. {d['judul_laporan']}")
            st.markdown(f"<div class='src'>{s.url}</div>", unsafe_allow_html=True)
            for c in s.catatan:
                (st.warning if "tidak bisa" in c or "gagal" in c else st.caption)(c)
            if h["sisa"]:
                st.warning("Placeholder di template yang tidak terisi: " + ", ".join(h["sisa"]))

            tab_sumber, tab_laporan, tab_saran = st.tabs(["Ringkasan sumber", "Peristiwa", "Dampak & rekomendasi"])
            with tab_sumber:
                st.write(d["ringkasan_sumber"])
                if s.gambar:
                    st.image([g.data for g in s.gambar], width=220)
                if s.teks:
                    with st.expander("Teks asli yang diambil"):
                        st.text(s.teks[:5000])
            with tab_laporan:
                st.markdown(f"**{d['tanggal_surat']} · {d['wilayah']} · {d['waktu']}**")
                st.write(d["latar_belakang"])
                c1, c2 = st.columns(2)
                with c1:
                    daftar("Pokok peristiwa", d["pokok_peristiwa"])
                    daftar("Pihak terkait", d["pihak_terkait"])
                with c2:
                    daftar("Lokasi", d["lokasi"])
                    st.markdown("**Sentimen publik**")
                    st.write(d["sentimen_publik"])
            with tab_saran:
                daftar("Dampak", d["dampak"])
                daftar("Potensi risiko", d["potensi_risiko"])
                daftar("Rekomendasi", d["rekomendasi"])

            st.download_button("Unduh dokumen Word", h["docx"], nama_file(d["judul_laporan"]),
                               "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                               key=f"dl_{i}")
