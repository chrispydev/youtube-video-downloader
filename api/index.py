import os
import threading
import time
import uuid

from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
from yt_dlp import YoutubeDL

app = FastAPI()

# ----------------------
# CORS
# ----------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for dev
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ----------------------
# Models
# ----------------------
class VideoRequest(BaseModel):
    url: str


class DownloadRequest(BaseModel):
    url: str
    format_id: str
    subtitle_lang: str = "en"
    has_audio: bool = False


# ----------------------
# Auto-delete downloaded file after error
# ----------------------
def delete_file_after_error(filepath: str):
    def delete_task():
        time.sleep(5)
        if os.path.exists(filepath):
            try:
                os.remove(filepath)
            except:
                pass

    threading.Thread(target=delete_task, daemon=True).start()


# ----------------------
# Auto-delete downloaded file after download
# ----------------------
def delete_file_after_delay(filepath: str, delay: int = 30):
    def delete_task():
        time.sleep(delay)
        if os.path.exists(filepath):
            try:
                os.remove(filepath)
            except:
                pass

    threading.Thread(target=delete_task, daemon=True).start()


# ----------------------
# INFO ENDPOINT
# ----------------------
@app.post("/info")
async def get_video_info(data: VideoRequest):
    url = data.url

    ydl_opts = {
        "quiet": True,
        "skip_download": True,
        "extractor_args": {
            "youtube": {"player_client": "web", "language": "en"}
        },  # Force English for extractor pages
        "noplaylist": True,
        # Request English subtitles metadata so frontend can show availability
        "writesubtitles": True,
        "writeautomaticsub": True,
        "subtitleslangs": ["en"],
        "subtitlesformat": "srt",
    }

    try:
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)

        # Extract usable formats safely and deduplicate similar entries (e.g. multiple entries
        # for the same resolution+ext). We keep the entry with the largest filesize when possible.
        raw_formats = [
            f for f in info.get("formats", []) if f.get("format_id") and f.get("url")
        ]
        fmt_map = {}
        for f in raw_formats:
            key = (f.get("ext"), f.get("resolution") or f.get("format_note") or "N/A")
            existing = fmt_map.get(key)
            if not existing:
                fmt_map[key] = f
            else:
                # Prefer the one with larger filesize (if filesize present)
                if (f.get("filesize") or 0) > (existing.get("filesize") or 0):
                    fmt_map[key] = f

        formats = [
            {
                "format_id": fv.get("format_id"),
                "ext": fv.get("ext"),
                "resolution": fv.get("resolution") or fv.get("format_note") or "N/A",
                # Prefer exact filesize when available, otherwise use filesize_approx
                "filesize": fv.get("filesize") or fv.get("filesize_approx"),
                "format_note": fv.get("format_note"),
                "has_audio": True
                if fv.get("acodec") and fv.get("acodec") != "none"
                else False,
                "has_video": True
                if fv.get("vcodec") and fv.get("vcodec") != "none"
                else False,
            }
            for fv in fmt_map.values()
        ]

        # Sort formats to provide a consistent ordering for the frontend.
        # This sorts primarily by resolution label (string) and then by extension.
        formats.sort(key=lambda x: (x.get("resolution") or "", x.get("ext") or ""))

        # Determine a sensible top-level filesize:
        # prefer `info.filesize` if present, otherwise take the largest filesize
        # from the available formats (filesize or filesize_approx).
        top_size = info.get("filesize")
        if not top_size:
            try:
                max_size = max(
                    (fv.get("filesize") or fv.get("filesize_approx") or 0)
                    for fv in fmt_map.values()
                )
                top_size = max_size if max_size > 0 else None
            except Exception:
                top_size = None

        # Gather subtitle language info so the frontend can present language options.
        subs = info.get("subtitles") or {}
        auto_caps = info.get("automatic_captions") or {}
        subtitle_langs = set()
        subtitle_langs.update(subs.keys())
        subtitle_langs.update(auto_caps.keys())
        subtitle_languages = sorted(list(subtitle_langs))

        return JSONResponse(
            {
                "title": info.get("title"),
                "thumbnail": info.get("thumbnail"),
                "duration": info.get("duration"),
                "uploader": info.get("uploader"),
                "description": info.get("description"),
                "formats": formats,
                # Top-level size: either reported by the extractor or inferred from formats
                "size": top_size,
                # Provide available subtitle languages and raw subtitle info for frontend use
                "subtitle_languages": subtitle_languages,
                "subtitles": subs,
                "automatic_captions": auto_caps,
            }
        )

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ----------------------
# DOWNLOAD ENDPOINT
# ----------------------
@app.post("/download")
async def download_video(req: DownloadRequest, background_tasks: BackgroundTasks):
    url = req.url
    format_id = req.format_id

    # Ensure downloads folder exists
    os.makedirs("downloads", exist_ok=True)
    output_filename = f"downloads/{uuid.uuid4()}.mp4"

    ydl_opts = {
        "outtmpl": output_filename,
        "format": format_id,  # Use selected format_id from frontend (may be adjusted below)
        "merge_output_format": "mp4",
        "quiet": True,
        # Subtitle handling - use requested subtitle_lang if provided
        "writesubtitles": True if getattr(req, "subtitle_lang", None) else False,
        "writeautomaticsub": True,
        "subtitleslangs": [req.subtitle_lang]
        if getattr(req, "subtitle_lang", None)
        else [],
        "subtitlesformat": "srt",
        "embedsubtitles": True,
        "postprocessors": [{"key": "FFmpegEmbedSubtitle"}],
        "prefer_ffmpeg": True,
    }

    # Inspect the video's formats to see if the selected format has audio.
    # If the selected format is video-only, ask yt-dlp to merge it with the best audio stream.
    try:
        with YoutubeDL({"quiet": True, "skip_download": True}) as ydl:
            info_check = ydl.extract_info(url, download=False)
        selected_fmt = None
        for f in info_check.get("formats", []):
            if f.get("format_id") == format_id:
                selected_fmt = f
                break
        has_audio_flag = False
        if selected_fmt:
            acodec = selected_fmt.get("acodec")
            has_audio_flag = acodec is not None and acodec != "none"
        # If format lacks audio, request merging with best audio
        if not has_audio_flag:
            ydl_opts["format"] = f"{format_id}+bestaudio/best"
    except Exception:
        # If we couldn't inspect formats, fall back to the provided format id
        pass

    try:
        with YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

        # Schedule auto-delete after 10 minutes
        background_tasks.add_task(delete_file_after_delay, output_filename)

        return FileResponse(
            output_filename, filename="video.mp4", media_type="video/mp4"
        )

    except Exception as e:
        # Schedule auto-delete after 10 minutes
        background_tasks.add_task(delete_file_after_error, output_filename)
        raise HTTPException(status_code=400, detail=str(e))
