"""Pengaturan dari file .env (lokal) atau st.secrets (Streamlit Cloud). API key tidak pernah ditulis di kode."""

from __future__ import annotations

import os

from dotenv import load_dotenv

load_dotenv()


def _get(name: str, default: str = "") -> str:
    value = os.getenv(name)
    if value is None:
        try:  # Streamlit Cloud menyimpan rahasia di st.secrets
            import streamlit as st
            value = st.secrets.get(name)
        except Exception:  # noqa: BLE001 - st.secrets melempar error kalau file secrets tidak ada
            value = None
    return (value or default).strip()


GEMINI_API_KEY = _get("GEMINI_API_KEY")

# Dicoba berurutan: kalau model pertama sibuk (503/429) atau tidak tersedia (404), lanjut ke berikutnya.
GEMINI_MODELS = [m.strip() for m in _get(
    "GEMINI_MODELS", "gemini-3.6-flash,gemini-3.5-flash,gemini-3.5-flash-lite").split(",") if m.strip()]

TEMPLATE_PATH = _get("REPORT_TEMPLATE", "templates/laporan_contoh.docx")
WILAYAH = _get("REPORT_WILAYAH", "Kota Surakarta")
