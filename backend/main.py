from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
from yt_dlp import YoutubeDL
import os
import uuid
import threading
import time
from fastapi.middleware.cors import CORSMiddleware

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


# ----------------------
# Auto-delete downloaded file after 10 minutes
# ----------------------
def delete_file_after_delay(filepath: str, delay: int = 600):
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
        },  # Force English
        "noplaylist": True,
    }

    try:
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)

        # Extract usable formats safely
        formats = [
            {
                "format_id": f.get("format_id"),
                "ext": f.get("ext"),
                "resolution": f.get("resolution") or f.get("format_note") or "N/A",
                "filesize": f.get("filesize"),
                "format_note": f.get("format_note"),
            }
            for f in info.get("formats", [])
            if f.get("format_id") and f.get("url")
        ]

        return JSONResponse(
            {
                "title": info.get("title"),
                "thumbnail": info.get("thumbnail"),
                "duration": info.get("duration"),
                "uploader": info.get("uploader"),
                "description": info.get("description"),
                "formats": formats,
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
        "format": format_id,  # Use selected format_id from frontend
        "merge_output_format": "mp4",
        "quiet": True,
    }

    try:
        with YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

        # Schedule auto-delete after 10 minutes
        background_tasks.add_task(delete_file_after_delay, output_filename)

        return FileResponse(
            output_filename, filename="video.mp4", media_type="video/mp4"
        )

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
