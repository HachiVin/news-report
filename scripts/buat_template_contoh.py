"""Membuat templates/laporan_contoh.docx: template contoh yang netral untuk demo publik.

    python scripts/buat_template_contoh.py

Template sendiri cukup ditulis di Word dengan placeholder {{ nama_field }} (lihat newsreport/document.py).
"""

from pathlib import Path

import docx
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Pt

OUT = Path(__file__).resolve().parent.parent / "templates" / "laporan_contoh.docx"


def heading(doc, text):
    p = doc.add_paragraph()
    r = p.add_run(text)
    r.bold, r.font.size = True, Pt(11)


def main() -> None:
    doc = docx.Document()
    style = doc.styles["Normal"]
    style.font.name, style.font.size = "Calibri", Pt(11)

    t = doc.add_paragraph()
    t.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = t.add_run("LAPORAN RINGKAS PEMBERITAAN")
    r.bold, r.font.size = True, Pt(14)
    s = doc.add_paragraph("{{ judul_laporan }}")
    s.alignment = WD_ALIGN_PARAGRAPH.CENTER
    m = doc.add_paragraph("Wilayah: {{ wilayah }} · Waktu peristiwa: {{ waktu }}")
    m.alignment = WD_ALIGN_PARAGRAPH.CENTER

    heading(doc, "I. Ringkasan Sumber")
    doc.add_paragraph("{{ ringkasan_sumber }}")
    heading(doc, "II. Latar Belakang")
    doc.add_paragraph("{{ latar_belakang }}")
    heading(doc, "III. Pokok Peristiwa")
    doc.add_paragraph("{{ pokok_peristiwa }}")
    heading(doc, "IV. Pihak dan Lokasi")
    doc.add_paragraph("Pihak terkait:")
    doc.add_paragraph("{{ pihak_terkait }}")
    doc.add_paragraph("Lokasi:")
    doc.add_paragraph("{{ lokasi }}")
    heading(doc, "V. Sentimen Publik")
    doc.add_paragraph("{{ sentimen_publik }}")
    heading(doc, "VI. Dampak dan Potensi Risiko")
    doc.add_paragraph("Dampak:")
    doc.add_paragraph("{{ dampak }}")
    doc.add_paragraph("Potensi risiko:")
    doc.add_paragraph("{{ potensi_risiko }}")
    heading(doc, "VII. Rekomendasi")
    doc.add_paragraph("{{ rekomendasi }}")

    tbl = doc.add_table(rows=1, cols=2)
    tbl.rows[0].cells[1].paragraphs[0].text = "Surakarta, {{ tanggal_surat }}"
    tbl.rows[0].cells[1].add_paragraph("Penyusun,")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    doc.save(OUT)
    print(f"template -> {OUT}")


if __name__ == "__main__":
    main()
