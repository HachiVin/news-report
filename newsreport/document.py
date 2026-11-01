"""Mengisi template Word laporan. Placeholder ditulis {{ nama_field }} di template.docx."""

from __future__ import annotations

import io
import re

import docx
from docx.shared import Pt

# Placeholder satu nilai
TEKS = ["judul_laporan", "latar_belakang", "waktu", "sentimen_publik", "tanggal_surat", "wilayah",
        "ringkasan_sumber"]

# Placeholder daftar dan gaya penomorannya: "angka" -> 1. 2.  "kurung" -> 1) 2)  "huruf" -> a. b.
DAFTAR = {
    "pokok_peristiwa": "angka", "pihak_terkait": "kurung", "lokasi": "kurung",
    "dampak": "huruf", "potensi_risiko": "huruf", "rekomendasi": "angka",
}


def _tag(name: str) -> str:
    return "{{ " + name + " }}"


def _semua_paragraf(doc):
    yield from doc.paragraphs
    for t in doc.tables:
        for row in t.rows:
            for cell in row.cells:
                yield from cell.paragraphs


def ganti_teks(doc, tag: str, nilai: str) -> None:
    """Ganti tag di run yang memuatnya, supaya format (tebal, font) tetap. Kalau tag terpecah di beberapa run,
    seluruh paragraf ditulis ulang dengan format run pertama."""
    for p in _semua_paragraf(doc):
        if tag not in p.text:
            continue
        for run in p.runs:
            if tag in run.text:
                run.text = run.text.replace(tag, nilai)
        if tag in p.text:
            full = p.text.replace(tag, nilai)
            for run in p.runs[1:]:
                run._r.getparent().remove(run._r)
            p.runs[0].text = full


def _label(i: int, gaya: str) -> str:
    if gaya == "huruf":
        return f"{'abcdefghijklmnopqrstuvwxyz'[i % 26]}. "
    if gaya == "kurung":
        return f"{i + 1}) "
    return f"{i + 1}. "


def ganti_daftar(doc, tag: str, items: list[str], gaya: str) -> None:
    target = next((p for p in _semua_paragraf(doc) if tag in p.text), None)
    if target is None:
        return
    fmt = target.paragraph_format
    for i, item in enumerate(items):
        p = target.insert_paragraph_before(f"{_label(i, gaya)}{item}", style=target.style)
        pf = p.paragraph_format
        pf.left_indent, pf.first_line_indent = fmt.left_indent, fmt.first_line_indent
        pf.space_before, pf.space_after, pf.line_spacing = fmt.space_before, fmt.space_after, fmt.line_spacing
        for r in p.runs:
            r.font.name, r.font.size = "Calibri", Pt(11)
    target._element.getparent().remove(target._element)


def isi_template(template: bytes, data: dict) -> bytes:
    doc = docx.Document(io.BytesIO(template))
    for name in TEKS:
        ganti_teks(doc, _tag(name), str(data.get(name, "")))
    for name, gaya in DAFTAR.items():
        ganti_daftar(doc, _tag(name), list(data.get(name, [])), gaya)
    out = io.BytesIO()
    doc.save(out)
    return out.getvalue()


def sisa_placeholder(docx_bytes: bytes) -> list[str]:
    """Placeholder yang masih tertinggal (tanda template memakai nama field yang tidak dikenal)."""
    doc = docx.Document(io.BytesIO(docx_bytes))
    text = "\n".join(p.text for p in _semua_paragraf(doc))
    return sorted(set(re.findall(r"\{\{\s*[a-zA-Z0-9_]+\s*\}\}", text)))


def nama_file(judul: str, nomor: int | None = None) -> str:
    aman = re.sub(r"[^A-Za-z0-9 _-]", "", judul).strip()[:40].strip() or "Laporan"
    return f"Laporan_{nomor}_{aman}.docx" if nomor else f"Laporan_{aman}.docx"
