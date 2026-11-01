from newsreport.sources import Sumber, deteksi_jenis, meta, parse_instagram, youtube_watch_url


def test_deteksi_jenis():
    assert deteksi_jenis("https://www.instagram.com/p/abc/") == "instagram"
    assert deteksi_jenis("https://vt.tiktok.com/ZS123/") == "tiktok"
    assert deteksi_jenis("https://youtu.be/dQw4w9WgXcQ") == "youtube"
    assert deteksi_jenis("https://m.youtube.com/watch?v=dQw4w9WgXcQ") == "youtube"
    assert deteksi_jenis("https://news.detik.com/berita/d-1") == "web"
    assert deteksi_jenis("https://fakeinstagram.com.evil.net/x") == "web"


def test_youtube_watch_url_normalises_every_form():
    want = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    for url in ("https://youtu.be/dQw4w9WgXcQ?si=xyz", "https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=30",
                "https://youtube.com/shorts/dQw4w9WgXcQ", "https://www.youtube.com/live/dQw4w9WgXcQ"):
        assert youtube_watch_url(url) == want
    assert youtube_watch_url("https://www.youtube.com/@channelname") is None


def test_meta_any_attribute_order_and_entities():
    html = ('<meta content="Judul &amp; berita" property="og:title">'
            '<meta property="og:image" content="https://cdn.x/img.jpg">')
    assert meta(html, "og:title") == "Judul & berita"
    assert meta(html, "og:image") == "https://cdn.x/img.jpg"
    assert meta(html, "og:description") is None


def test_parse_instagram_caption_and_image():
    html = ('<meta property="og:title" content="Akun Berita on Instagram">'
            '<meta property="og:description" content="1,234 likes, 56 comments - akunberita on October 1, 2026: '
            '&quot;Demo buruh di Balai Kota Surakarta, Kamis (1/10).&quot;">'
            '<meta property="og:image" content="https://cdn.ig/post.jpg">')
    judul, caption, img = parse_instagram(html)
    assert judul == "Akun Berita on Instagram"
    assert caption == "Demo buruh di Balai Kota Surakarta, Kamis (1/10)."
    assert img == "https://cdn.ig/post.jpg"


def test_dibaca_lists_what_was_read():
    s = Sumber(url="u", jenis="youtube", teks="judul", video_uri="https://www.youtube.com/watch?v=x")
    assert s.dibaca == ["teks", "video"]
