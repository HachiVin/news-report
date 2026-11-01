# News-to-Report Generator

Turns news links (web articles, Instagram posts, TikTok, YouTube) into a **structured news report in Word**.
Gemini reads the article text, the post image and the video itself, fills a fixed report schema, and the
app writes it into a Word template. A person checks the draft instead of writing it from scratch.

Built first as a paid freelance tool for a client who needed internal reports drafted from news coverage.
This public version uses a neutral sample template and report format; the client's own template is not
included.

## How it works

1. **Read the source** (`newsreport/sources.py`), per link type:

   | Link | What is read |
   |---|---|
   | News site | Full article text (`trafilatura`) |
   | Instagram | Caption + main image (text inside the image is read too) |
   | TikTok | Caption + cover image (TikTok video itself cannot be fetched) |
   | YouTube | The video itself, picture and sound, read by Gemini |

2. **Draft the report with Gemini** (`newsreport/analyzer.py`). Text, images and video go in one
   multimodal request. The answer must follow the Pydantic schema `LaporanBerita` (structured output), so
   every section of the report lands in the right place.
3. **Fill the Word template** (`newsreport/document.py`). `{{ field }}` placeholders are replaced, lists get
   numbered (1. / 1) / a.), and the template's paragraph formatting is kept.

## Guard rails

- **No invented facts.** Anything not in the source is written as *"Tidak disebutkan dalam sumber"*.
- **Source summary first.** Each report opens with a factual summary of the source, so the reader can check
  the rest against it.
- **Report date from the calendar**, not guessed by the model.
- **Rejected videos** (private, age-restricted, too long) do not fail the run: the report falls back to the
  title and the app shows a warning.
- **Fallback models.** If one Gemini model is busy (503/429) or unavailable (404), the next one is used.

## Run it

```powershell
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env        # then put your GEMINI_API_KEY in .env
streamlit run app.py
```

On Streamlit Community Cloud, set `GEMINI_API_KEY` in the app's **Secrets** instead of `.env`.

Tests (no network, no Gemini calls):

```powershell
pip install -r requirements-dev.txt
pytest
```

To use your own report format, write a Word file with the placeholders listed in `newsreport/document.py`
and upload it in the sidebar, or regenerate the sample with `python scripts/buat_template_contoh.py`.

## Layout

```
app.py                         Streamlit UI
newsreport/config.py           settings from .env or Streamlit secrets
newsreport/schema.py           report schema (structured output)
newsreport/sources.py          text, image and video from a link
newsreport/analyzer.py         prompt, Gemini call, retries and fallback models
newsreport/document.py         Word template filling
templates/laporan_contoh.docx  neutral sample template
scripts/buat_template_contoh.py
tests/                         offline tests
```

## Limits

- The output is a **draft**; impact, risk and recommendations still need a person's judgement.
- Instagram sometimes blocks access without login; only the first image of a carousel is read, and reels
  video is not.
- YouTube videos must be public, and the Gemini free tier caps how much video can be read per day.
- Nothing is evaluated yet against human-written reports; a small scored test set is the next step.
