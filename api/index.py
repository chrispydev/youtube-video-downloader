# main.py  (rename your file or replace content)
import os
import threading
import time
import uuid
import base64
from io import StringIO
from fastapi import FastAPI, Form, HTTPException, Request, BackgroundTasks
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from yt_dlp import YoutubeDL

app = FastAPI()

# Mount templates folder (create a 'templates' folder next to main.py)
templates = Jinja2Templates(directory="templates")

# CORS (optional if you keep React later)
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ----------------------
# Cookie helper (same as before)
# ----------------------
def get_cookie_file():
    cookies_base64 = os.getenv("YOUTUBE_COOKIES_BASE64")
    if not cookies_base64:
        return None
    try:
        decoded = base64.b64decode(cookies_base64).decode("utf-8")
        return StringIO(decoded)
    except:
        return None


# File cleanup helpers (same)
def delete_file_after_delay(filepath: str, delay: int = 40):
    def task():
        time.sleep(delay)
        if os.path.exists(filepath):
            os.remove(filepath)

    threading.Thread(target=task, daemon=True).start()


def delete_file_after_error(filepath: str):
    delete_file_after_delay(filepath, 5)


# ----------------------
# HOME - full page
# ----------------------
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse(
        "index.html", {"request": request, "status": "", "info": None}
    )


# ----------------------
# GET INFO (POST from form)
# ----------------------
@app.post("/get-info", response_class=HTMLResponse)
async def get_info(request: Request, url: str = Form(...)):
    cookies_content = get_cookie_file()
    ydl_opts = {
        "quiet": True,
        "skip_download": True,
        "extractor_args": {"youtube": {"player_client": ["ios", "android", "web"]}},
        "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) ... Safari/604.1",
        "referer": "https://www.youtube.com/",
        "noplaylist": True,
    }
    if cookies_content:
        ydl_opts["cookiefile"] = cookies_content

    try:
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)

        # Process formats (your logic, simplified a bit)
        formats = []
        seen = set()
        for f in info.get("formats", []):
            key = (f.get("ext"), f.get("resolution") or f.get("format_note"))
            if key not in seen and f.get("url"):
                seen.add(key)
                formats.append(
                    {
                        "format_id": f["format_id"],
                        "ext": f["ext"],
                        "resolution": f.get("resolution")
                        or f.get("format_note")
                        or "audio-only",
                        "filesize": f.get("filesize") or f.get("filesize_approx"),
                        "has_audio": f.get("acodec", "none") != "none",
                    }
                )

        formats.sort(key=lambda x: (x["resolution"] or "", -(x["filesize"] or 0)))

        subtitle_langs = sorted(
            set((info.get("subtitles") or {}) | (info.get("automatic_captions") or {}))
        )

        video_info = {
            "title": info.get("title"),
            "thumbnail": info.get("thumbnail"),
            "duration": info.get("duration"),
            "uploader": info.get("uploader"),
            "formats": formats,
            "subtitle_languages": subtitle_langs,
        }

        return templates.TemplateResponse(
            "index.html",
            {
                "request": request,
                "info": video_info,
                "url": url,
                "status": "Info loaded!",
            },
        )

    except Exception as e:
        return templates.TemplateResponse(
            "index.html",
            {"request": request, "status": f"Error: {str(e)}", "info": None},
        )


# ----------------------
# DOWNLOAD (POST)
# ----------------------
@app.post("/download")
async def download(
    background_tasks: BackgroundTasks,
    url: str = Form(...),
    format_id: str = Form(...),
    subtitle_lang: str = Form("en"),
):
    cookies_content = get_cookie_file()
    os.makedirs("downloads", exist_ok=True)
    output_filename = f"downloads/{uuid.uuid4()}.mp4"

    ydl_opts = {
        "outtmpl": output_filename,
        "format": format_id,
        "merge_output_format": "mp4",
        "writesubtitles": True,
        "writeautomaticsub": True,
        "subtitleslangs": [subtitle_lang],
        "subtitlesformat": "srt",
        "embedsubtitles": True,
        "postprocessors": [{"key": "FFmpegEmbedSubtitle"}],
    }
    if cookies_content:
        ydl_opts["cookiefile"] = cookies_content

    try:
        with YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

        background_tasks.add_task(delete_file_after_delay, output_filename)
        return FileResponse(
            output_filename, filename="video.mp4", media_type="video/mp4"
        )

    except Exception as e:
        background_tasks.add_task(delete_file_after_error, output_filename)
        raise HTTPException(400, detail=str(e))


# Health
@app.get("/health")
def health():
    return {"status": "ok"}
