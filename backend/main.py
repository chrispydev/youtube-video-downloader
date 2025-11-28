from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from yt_dlp import YoutubeDL
import os
import uuid
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class VideoRequest(BaseModel):
    url: str


class DownloadRequest(BaseModel):
    url: str
    format_id: str


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


@app.post("/download")
async def download_video(req: DownloadRequest):
    url = req.url
    format_id = req.format_id

    # temporary unique filename
    output_filename = f"downloads/{uuid.uuid4()}.mp4"
    os.makedirs("downloads", exist_ok=True)

    ydl_opts = {
        "outtmpl": output_filename,
        "format": format_id,
        "merge_output_format": "mp4",
    }

    try:
        with YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

        return FileResponse(output_filename, filename="video.mp4")

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
