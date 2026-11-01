"""Mengambil isi berita dari sebuah link: teks, gambar, dan (untuk YouTube) video yang dibaca langsung oleh Gemini.

Apa yang terbaca per jenis link:
- Web berita : isi artikel lengkap.
- Instagram  : caption + gambar utama postingan (teks di dalam gambar ikut terbaca oleh Gemini).
- TikTok     : caption + gambar sampul video (isi video TikTok tidak bisa diambil).
- YouTube    : isi video (gambar dan suara) dibaca langsung oleh Gemini, ditambah judul dan nama channel.
"""

from __future__ import annotations

import html as htmllib
import json
import re
import urllib.parse
import urllib.request
from dataclasses import dataclass, field

import trafilatura

UA_BROWSER = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/130.0 Safari/537.36")
UA_PREVIEW = "facebookexternalhit/1.1 (+http://www.facebook.com/externalhit_uatext.php)"
MAX_IMAGE_BYTES = 8_000_000
TIMEOUT = 15


@dataclass
class Gambar:
    data: bytes
    mime_type: str


@dataclass
class Sumber:
    url: str
    jenis: str  # "web" | "instagram" | "tiktok" | "youtube"
    judul: str = ""
    teks: str = ""
    gambar: list[Gambar] = field(default_factory=list)
    video_uri: str | None = None
    catatan: list[str] = field(default_factory=list)  # apa yang terbaca dan apa yang tidak

    @property
    def dibaca(self) -> list[str]:
        out = []
        if self.teks.strip():
            out.append("teks")
        if self.gambar:
            out.append(f"{len(self.gambar)} gambar")
        if self.video_uri:
            out.append("video")
        return out


# ---------- pembantu ----------

def _get(url: str, user_agent: str = UA_BROWSER, accept: str = "*/*") -> tuple[bytes, str]:
    req = urllib.request.Request(url, headers={
        "User-Agent": user_agent, "Accept": accept,
        "Accept-Language": "id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7"})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        return resp.read(MAX_IMAGE_BYTES + 1), resp.headers.get("Content-Type", "")


def meta(html: str, name: str) -> str | None:
    """Nilai <meta property|name="..." content="...">, urutan atribut bebas."""
    for pattern in (
        rf'<meta[^>]+(?:property|name)=["\']{re.escape(name)}["\'][^>]*content=["\']([^"\']*)["\']',
        rf'<meta[^>]+content=["\']([^"\']*)["\'][^>]*(?:property|name)=["\']{re.escape(name)}["\']',
    ):
        m = re.search(pattern, html, re.IGNORECASE)
        if m:
            return htmllib.unescape(m.group(1)).strip()
    return None


def unduh_gambar(url: str | None) -> Gambar | None:
    if not url:
        return None
    try:
        data, ctype = _get(url, accept="image/*")
    except Exception:
        return None
    mime = ctype.split(";")[0].strip().lower()
    if not mime.startswith("image/") or len(data) > MAX_IMAGE_BYTES or not data:
        return None
    return Gambar(data=data, mime_type=mime)


def deteksi_jenis(url: str) -> str:
    host = urllib.parse.urlparse(url.strip()).netloc.lower()
    if host.endswith("instagram.com"):
        return "instagram"
    if host.endswith("tiktok.com"):
        return "tiktok"
    if host.endswith(("youtube.com", "youtu.be")):
        return "youtube"
    return "web"


def youtube_watch_url(url: str) -> str | None:
    """Bentuk baku https://www.youtube.com/watch?v=ID dari link youtu.be, shorts, live, atau watch."""
    p = urllib.parse.urlparse(url.strip())
    host = p.netloc.lower()
    vid = None
    if host.endswith("youtu.be"):
        vid = p.path.strip("/").split("/")[0]
    elif host.endswith("youtube.com"):
        if p.path == "/watch":
            vid = urllib.parse.parse_qs(p.query).get("v", [None])[0]
        else:
            m = re.match(r"^/(?:shorts|live|embed)/([^/?#]+)", p.path)
            vid = m.group(1) if m else None
    if vid and re.fullmatch(r"[A-Za-z0-9_-]{6,20}", vid):
        return f"https://www.youtube.com/watch?v={vid}"
    return None


def _oembed(endpoint: str, url: str) -> dict:
    data, _ = _get(f"{endpoint}?url={urllib.parse.quote(url, safe='')}&format=json", accept="application/json")
    return json.loads(data.decode("utf-8", errors="ignore"))


# ---------- per jenis link ----------

def ambil_web(url: str) -> Sumber:
    downloaded = trafilatura.fetch_url(url)
    if not downloaded:
        raise ValueError("Halaman tidak bisa diunduh (situs menolak akses atau link salah).")
    teks = trafilatura.extract(downloaded, include_comments=False) or ""
    if not teks.strip():
        raise ValueError("Isi artikel tidak bisa diekstrak dari halaman ini.")
    judul = meta(downloaded, "og:title") or ""
    return Sumber(url=url, jenis="web", judul=judul, teks=teks.strip(),
                  catatan=["Isi artikel dibaca lengkap."])


def parse_instagram(html: str) -> tuple[str, str, str | None]:
    """(judul, caption, url gambar) dari HTML pratinjau Instagram."""
    raw = meta(html, "og:description") or meta(html, "description") or ""
    caption = raw
    # Formatnya: '123 likes, 4 comments - akun on 1 Oktober 2026: "isi caption"'
    m = re.search(r':\s*["“](.*)["”]\s*\.?\s*$', raw, re.DOTALL)
    if m:
        caption = m.group(1)
    if not caption.strip():
        ld = re.search(r'<script type="application/ld\+json">(.*?)</script>', html, re.DOTALL)
        if ld:
            try:
                obj = json.loads(ld.group(1))
                caption = obj.get("caption") or obj.get("description") or ""
            except (ValueError, AttributeError):
                pass
    return meta(html, "og:title") or "Postingan Instagram", caption.strip(), meta(html, "og:image")


def ambil_instagram(url: str) -> Sumber:
    clean = url.split("?")[0].rstrip("/") + "/"
    try:
        data, _ = _get(clean, user_agent=UA_PREVIEW, accept="text/html")
    except Exception as e:
        raise ValueError(f"Instagram tidak bisa diakses: {e}") from e
    judul, caption, img_url = parse_instagram(data.decode("utf-8", errors="ignore"))
    gambar = unduh_gambar(img_url)
    if not caption and not gambar:
        raise ValueError("Instagram membatasi akses (akun privat atau perlu login).")
    s = Sumber(url=clean, jenis="instagram", judul=judul, teks=caption, gambar=[gambar] if gambar else [])
    s.catatan.append("Caption dan gambar utama dibaca." if gambar else "Hanya caption yang terbaca; gambar gagal diunduh.")
    s.catatan.append("Slide berikutnya pada carousel dan isi video reels tidak ikut terbaca.")
    return s


def ambil_tiktok(url: str) -> Sumber:
    try:
        info = _oembed("https://www.tiktok.com/oembed", url)
    except Exception as e:
        raise ValueError(f"TikTok tidak bisa diakses: {e}") from e
    gambar = unduh_gambar(info.get("thumbnail_url"))
    teks = f"Akun: @{info.get('author_name', '-')}\nCaption: {info.get('title', '')}".strip()
    s = Sumber(url=url, jenis="tiktok", judul=info.get("title", "Video TikTok")[:120], teks=teks,
               gambar=[gambar] if gambar else [])
    s.catatan.append("Caption dan gambar sampul dibaca; isi video TikTok tidak bisa diambil.")
    return s


def ambil_youtube(url: str) -> Sumber:
    watch = youtube_watch_url(url)
    if not watch:
        raise ValueError("Link YouTube tidak dikenali (harus link video, bukan channel atau playlist).")
    judul, teks = "Video YouTube", ""
    try:
        info = _oembed("https://www.youtube.com/oembed", watch)
        judul = info.get("title", judul)
        teks = f"Channel: {info.get('author_name', '-')}\nJudul video: {judul}"
    except Exception:
        pass  # judul hanya pelengkap; isi video tetap dibaca Gemini
    return Sumber(url=watch, jenis="youtube", judul=judul, teks=teks, video_uri=watch,
                  catatan=["Isi video (gambar dan suara) dibaca langsung oleh Gemini. Video harus publik."])


def ambil_sumber(url: str) -> Sumber:
    url = url.strip()
    if not url.lower().startswith(("http://", "https://")):
        raise ValueError("Link harus diawali http:// atau https://")
    jenis = deteksi_jenis(url)
    return {"instagram": ambil_instagram, "tiktok": ambil_tiktok,
            "youtube": ambil_youtube, "web": ambil_web}[jenis](url)
