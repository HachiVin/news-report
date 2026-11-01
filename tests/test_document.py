import io

import docx

from newsreport.document import isi_template, nama_file, sisa_placeholder


def make_template() -> bytes:
    d = docx.Document()
    p = d.add_paragraph()
    p.add_run("JUDUL: ").bold = True
    p.add_run("{{ judul_laporan }}").bold = True
    d.add_paragraph("{{ pokok_peristiwa }}")
    d.add_paragraph("{{ dampak }}")
    cell = d.add_table(rows=1, cols=1).rows[0].cells[0]
    cell.paragraphs[0].text = "Surakarta, {{ tanggal_surat }}"
    d.add_paragraph("{{ field_tak_dikenal }}")
    buf = io.BytesIO()
    d.save(buf)
    return buf.getvalue()


def test_isi_template_fills_text_lists_and_tables():
    data = {"judul_laporan": "AKSI DEMO BURUH", "tanggal_surat": "Oktober 2026",
            "pokok_peristiwa": ["Massa berkumpul", "Arus lalu lintas dialihkan"], "dampak": ["Lalu lintas tersendat"]}
    out = isi_template(make_template(), data)
    doc = docx.Document(io.BytesIO(out))
    texts = [p.text for p in doc.paragraphs]
    assert texts[0] == "JUDUL: AKSI DEMO BURUH"
    assert doc.paragraphs[0].runs[1].bold  # format run tetap
    assert "1. Massa berkumpul" in texts and "2. Arus lalu lintas dialihkan" in texts
    assert "a. Lalu lintas tersendat" in texts
    assert doc.tables[0].rows[0].cells[0].text == "Surakarta, Oktober 2026"
    assert sisa_placeholder(out) == ["{{ field_tak_dikenal }}"]


def test_nama_file_is_safe():
    assert nama_file("AKSI: DEMO/BURUH?", 2) == "Laporan_2_AKSI DEMOBURUH.docx"
    assert nama_file("???") == "Laporan_Laporan.docx"


def test_sample_template_has_only_known_placeholders():
    from pathlib import Path

    from newsreport.analyzer import tanggal_surat
    from newsreport.schema import LIST_FIELDS, LaporanBerita

    tpl = (Path(__file__).resolve().parent.parent / "templates" / "laporan_contoh.docx").read_bytes()
    data = {n: (["x"] if n in LIST_FIELDS else "x") for n in LaporanBerita.model_fields}
    data.update(tanggal_surat=tanggal_surat(), wilayah="Kota Surakarta")
    assert sisa_placeholder(isi_template(tpl, data)) == []
