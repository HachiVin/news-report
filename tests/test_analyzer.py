import json

import pytest

from newsreport.analyzer import Analis, bersihkan_butir, susun_parts, tanggal_surat
from newsreport.schema import LIST_FIELDS, TIDAK_ADA, LaporanBerita
from newsreport.sources import Gambar, Sumber

OK = {name: ([f"1. {name}"] if name in LIST_FIELDS else name) for name in LaporanBerita.model_fields}


class FakeModels:
    def __init__(self, behaviour):
        self.behaviour, self.calls = behaviour, []

    def generate_content(self, model, contents, config):
        parts = contents[0].parts
        self.calls.append((model, parts))
        result = self.behaviour(model, parts)
        if isinstance(result, Exception):
            raise result
        return type("R", (), {"text": json.dumps(result)})()


class FakeClient:
    def __init__(self, behaviour):
        self.models = FakeModels(behaviour)


def has_video(parts):
    return any(p.file_data for p in parts)


def test_parts_carry_text_images_and_video():
    s = Sumber(url="https://www.youtube.com/watch?v=abc123xyz", jenis="youtube", teks="Judul video: X",
               gambar=[Gambar(b"\x89PNG", "image/png")], video_uri="https://www.youtube.com/watch?v=abc123xyz")
    parts = susun_parts(s, "Wilayah Hukum Kota Surakarta")
    assert "Judul video: X" in parts[0].text and TIDAK_ADA in parts[0].text
    assert parts[1].inline_data.mime_type == "image/png"
    assert parts[2].file_data.file_uri == s.video_uri
    assert not has_video(susun_parts(s, "W", pakai_video=False))


def test_lists_are_cleaned_and_date_comes_from_calendar():
    client = FakeClient(lambda m, p: dict(OK, pihak_terkait=["a. Mahasiswa", "- Buruh"], rekomendasi=[]))
    data = Analis(client, ["m1"], "W", sleep=lambda s: None).analisis(Sumber(url="u", jenis="web", teks="t"))
    assert data["pihak_terkait"] == ["Mahasiswa", "Buruh"]
    assert data["rekomendasi"] == [TIDAK_ADA]
    assert data["wilayah"] == "W"
    assert data["tanggal_surat"] == tanggal_surat()


def test_busy_model_is_retried_then_next_model_used():
    def behaviour(model, parts):
        return RuntimeError("503 UNAVAILABLE") if model == "m1" else OK
    client = FakeClient(behaviour)
    Analis(client, ["m1", "m2"], "W", sleep=lambda s: None).analisis(Sumber(url="u", jenis="web", teks="t"))
    assert [c[0] for c in client.models.calls] == ["m1", "m1", "m2"]


def test_rejected_video_falls_back_to_title_with_a_warning():
    def behaviour(model, parts):
        return RuntimeError("400 INVALID_ARGUMENT video is private") if has_video(parts) else OK
    s = Sumber(url="v", jenis="youtube", teks="Judul video: X", video_uri="https://www.youtube.com/watch?v=abc123xyz")
    client = FakeClient(behaviour)
    Analis(client, ["m1", "m2"], "W", sleep=lambda s: None).analisis(s)
    assert [has_video(c[1]) for c in client.models.calls] == [True, False]
    assert any("Video tidak bisa dibaca" in c for c in s.catatan)


def test_other_errors_are_raised():
    client = FakeClient(lambda m, p: RuntimeError("401 API key not valid"))
    with pytest.raises(RuntimeError, match="API key"):
        Analis(client, ["m1"], "W", sleep=lambda s: None).analisis(Sumber(url="u", jenis="web", teks="t"))


def test_bersihkan_butir():
    assert bersihkan_butir(["1) Satu", "b. Dua", "• Tiga", "  "]) == ["Satu", "Dua", "Tiga"]
