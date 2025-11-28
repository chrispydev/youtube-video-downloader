from fastapi import FastAPI, WebSocket, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from yt_dlp import YoutubeDL
import uuid
import os
import asyncio

app = FastAPI()

# ---------- CORS ----------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # replace "*" with your frontend URL in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------- Request Models ----------
class VideoRequest(BaseModel):
    url: str


class DownloadRequest(BaseModel):
    url: str
    format_id: str


# ---------- Info Endpoint ----------
@app.post("/info")
async def get_video_info(data: VideoRequest):
    url = data.url

    ydl_opts = {
        "quiet": True,
        "skip_download": True,
    }

    try:
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)

        return {
            "title": info.get("title"),
            "thumbnail": info.get("thumbnail"),
            "duration": info.get("duration"),
            "uploader": info.get("uploader"),
            "description": info.get("description"),
            "formats": [
                {
                    "format_id": f.get("format_id"),
                    "ext": f.get("ext"),
                    "resolution": f.get("resolution"),
                    "filesize": f.get("filesize"),
                    "format_note": f.get("format_note"),
                }
                for f in info.get("formats", [])
                if f.get("format_id")
            ],
        }

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ---------- WebSocket Download Endpoint ----------
@app.websocket("/ws/download")
async def websocket_download(websocket: WebSocket):
    await websocket.accept()
    try:
        data = await websocket.receive_json()
        url = data.get("url")
        format_id = data.get("format_id")

        if not url or not format_id:
            await websocket.send_json({"error": "url and format_id are required"})
            await websocket.close()
            return

        # Ensure downloads folder exists
        os.makedirs("downloads", exist_ok=True)
        output_file = f"downloads/{uuid.uuid4()}.mp4"

        # Progress hook for yt-dlp
        def progress_hook(d):
            if d["status"] == "downloading":
                percent = d.get("_percent_str", "0.0%")
                asyncio.create_task(websocket.send_json({"progress": percent}))
            elif d["status"] == "finished":
                asyncio.create_task(
                    websocket.send_json({"progress": "100%", "finished": True})
                )

        ydl_opts = {
            "format": format_id,
            "outtmpl": output_file,
            "merge_output_format": "mp4",
            "progress_hooks": [progress_hook],
        }

        with YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

        await websocket.send_json({"file": output_file})
        await websocket.close()

    except Exception as e:
        await websocket.send_json({"error": str(e)})
        await websocket.close()
