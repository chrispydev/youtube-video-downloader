import os
import threading
import time
import uuid
import base64
from io import StringIO
from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, HTMLResponse
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
# Cookie loading helper (loaded once, reused)
# ----------------------
def get_cookie_file():
    cookies_content = None
    cookies_base64 = os.getenv("YOUTUBE_COOKIES_BASE64")
    if cookies_base64:
        try:
            decoded = base64.b64decode(cookies_base64).decode("utf-8")
            cookies_content = StringIO(decoded)
            print("Cookies loaded successfully from environment variable")
        except Exception as e:
            print(f"Failed to decode cookies from env var: {e}")
    else:
        print("No YOUTUBE_COOKIES_BASE64 env var found - running without cookies")
    return cookies_content


# ----------------------
# Auto-delete helpers (unchanged)
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

    # Get cookies once
    cookies_content = get_cookie_file()

    ydl_opts = {
        "quiet": True,
        "skip_download": True,
        "extractor_args": {"youtube": {"player_client": "web", "language": "en"}},
        "noplaylist": True,
        "writesubtitles": True,
        "writeautomaticsub": True,
        "subtitleslangs": ["en"],
        "subtitlesformat": "srt",
    }

    # Apply cookies if available
    if cookies_content:
        ydl_opts["cookiefile"] = cookies_content

    try:
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)

        # Your existing format processing code (unchanged)
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
                if (f.get("filesize") or 0) > (existing.get("filesize") or 0):
                    fmt_map[key] = f

        formats = [
            {
                "format_id": fv.get("format_id"),
                "ext": fv.get("ext"),
                "resolution": fv.get("resolution") or fv.get("format_note") or "N/A",
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

        formats.sort(key=lambda x: (x.get("resolution") or "", x.get("ext") or ""))

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

        subs = info.get("subtitles") or {}
        auto_caps = info.get("automatic_captions") or {}
        subtitle_langs = set(subs.keys()) | set(auto_caps.keys())
        subtitle_languages = sorted(list(subtitle_langs))

        return JSONResponse(
            {
                "title": info.get("title"),
                "thumbnail": info.get("thumbnail"),
                "duration": info.get("duration"),
                "uploader": info.get("uploader"),
                "description": info.get("description"),
                "formats": formats,
                "size": top_size,
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

    # Get cookies once
    cookies_content = get_cookie_file()

    # Ensure downloads folder exists
    os.makedirs("downloads", exist_ok=True)
    output_filename = f"downloads/{uuid.uuid4()}.mp4"

    ydl_opts = {
        "outtmpl": output_filename,
        "format": format_id,
        "merge_output_format": "mp4",
        "quiet": True,
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

    # Apply cookies if available
    if cookies_content:
        ydl_opts["cookiefile"] = cookies_content

    # Inspect formats for audio check (unchanged)
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
        if not has_audio_flag:
            ydl_opts["format"] = f"{format_id}+bestaudio/best"
    except Exception:
        pass

    try:
        with YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        background_tasks.add_task(delete_file_after_delay, output_filename)
        return FileResponse(
            output_filename, filename="video.mp4", media_type="video/mp4"
        )
    except Exception as e:
        background_tasks.add_task(delete_file_after_error, output_filename)
        raise HTTPException(status_code=400, detail=str(e))


# Landing page (keep as-is)
@app.get("/", response_class=HTMLResponse)
def read_root():
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Vercel + FastAPI</title>
        <link rel="icon" type="image/x-icon" href="/favicon.ico">
        <style>
            * {
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }
            
            body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Oxygen', 'Ubuntu', 'Cantarell', sans-serif;
                background-color: #000000;
                color: #ffffff;
                line-height: 1.6;
                min-height: 100vh;
                display: flex;
                flex-direction: column;
            }
            
            header {
                border-bottom: 1px solid #333333;
                padding: 0;
            }
            
            nav {
                max-width: 1200px;
                margin: 0 auto;
                display: flex;
                align-items: center;
                padding: 1rem 2rem;
                gap: 2rem;
            }
            
            .logo {
                font-size: 1.25rem;
                font-weight: 600;
                color: #ffffff;
                text-decoration: none;
            }
            
            .nav-links {
                display: flex;
                gap: 1.5rem;
                margin-left: auto;
            }
            
            .nav-links a {
                text-decoration: none;
                color: #888888;
                padding: 0.5rem 1rem;
                border-radius: 6px;
                transition: all 0.2s ease;
                font-size: 0.875rem;
                font-weight: 500;
            }
            
            .nav-links a:hover {
                color: #ffffff;
                background-color: #111111;
            }
            
            main {
                flex: 1;
                max-width: 1200px;
                margin: 0 auto;
                padding: 4rem 2rem;
                display: flex;
                flex-direction: column;
                align-items: center;
                text-align: center;
            }
            
            .hero {
                margin-bottom: 3rem;
            }
            
            .hero-code {
                margin-top: 2rem;
                width: 100%;
                max-width: 900px;
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            }
            
            .hero-code pre {
                background-color: #0a0a0a;
                border: 1px solid #333333;
                border-radius: 8px;
                padding: 1.5rem;
                text-align: left;
                grid-column: 1 / -1;
            }
            
            h1 {
                font-size: 3rem;
                font-weight: 700;
                margin-bottom: 1rem;
                background: linear-gradient(to right, #ffffff, #888888);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                background-clip: text;
            }
            
            .subtitle {
                font-size: 1.25rem;
                color: #888888;
                margin-bottom: 2rem;
                max-width: 600px;
            }
            
            .cards {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
                gap: 1.5rem;
                width: 100%;
                max-width: 900px;
            }
            
            .card {
                background-color: #111111;
                border: 1px solid #333333;
                border-radius: 8px;
                padding: 1.5rem;
                transition: all 0.2s ease;
                text-align: left;
            }
            
            .card:hover {
                border-color: #555555;
                transform: translateY(-2px);
            }
            
            .card h3 {
                font-size: 1.125rem;
                font-weight: 600;
                margin-bottom: 0.5rem;
                color: #ffffff;
            }
            
            .card p {
                color: #888888;
                font-size: 0.875rem;
                margin-bottom: 1rem;
            }
            
            .card a {
                display: inline-flex;
                align-items: center;
                color: #ffffff;
                text-decoration: none;
                font-size: 0.875rem;
                font-weight: 500;
                padding: 0.5rem 1rem;
                background-color: #222222;
                border-radius: 6px;
                border: 1px solid #333333;
                transition: all 0.2s ease;
            }
            
            .card a:hover {
                background-color: #333333;
                border-color: #555555;
            }
            
            .status-badge {
                display: inline-flex;
                align-items: center;
                gap: 0.5rem;
                background-color: #0070f3;
                color: #ffffff;
                padding: 0.25rem 0.75rem;
                border-radius: 20px;
                font-size: 0.75rem;
                font-weight: 500;
                margin-bottom: 2rem;
            }
            
            .status-dot {
                width: 6px;
                height: 6px;
                background-color: #00ff88;
                border-radius: 50%;
            }
            
            pre {
                background-color: #0a0a0a;
                border: 1px solid #333333;
                border-radius: 6px;
                padding: 1rem;
                overflow-x: auto;
                margin: 0;
            }
            
            code {
                font-family: 'SF Mono', Monaco, 'Cascadia Code', 'Roboto Mono', Consolas, 'Courier New', monospace;
                font-size: 0.85rem;
                line-height: 1.5;
                color: #ffffff;
            }
            
            /* Syntax highlighting */
            .keyword {
                color: #ff79c6;
            }
            
            .string {
                color: #f1fa8c;
            }
            
            .function {
                color: #50fa7b;
            }
            
            .class {
                color: #8be9fd;
            }
            
            .module {
                color: #8be9fd;
            }
            
            .variable {
                color: #f8f8f2;
            }
            
            .decorator {
                color: #ffb86c;
            }
            
            @media (max-width: 768px) {
                nav {
                    padding: 1rem;
                    flex-direction: column;
                    gap: 1rem;
                }
                
                .nav-links {
                    margin-left: 0;
                }
                
                main {
                    padding: 2rem 1rem;
                }
                
                h1 {
                    font-size: 2rem;
                }
                
                .hero-code {
                    grid-template-columns: 1fr;
                }
                
                .cards {
                    grid-template-columns: 1fr;
                }
            }
        </style>
    </head>
    <body>
        <header>
            <nav>
                <a href="/" class="logo">Vercel + FastAPI</a>
                <div class="nav-links">
                    <a href="/docs">API Docs</a>
                    <a href="/api/data">API</a>
                </div>
            </nav>
        </header>
        <main>
            <div class="hero">
                <h1>Vercel + FastAPI</h1>
                <div class="hero-code">
                    <pre><code><span class="keyword">from</span> <span class="module">fastapi</span> <span class="keyword">import</span> <span class="class">FastAPI</span>

                    <span class="variable">app</span> = <span class="class">FastAPI</span>()

                    <span class="decorator">@app.get</span>(<span class="string">"/"</span>)
                    <span class="keyword">def</span> <span class="function">read_root</span>():
                    <span class="keyword">return</span> {<span class="string">"Python"</span>: <span class="string">"on Vercel"</span>}</code></pre>
                </div>
            </div>
            
            <div class="cards">
                <div class="card">
                    <h3>Interactive API Docs</h3>
                    <p>Explore this API's endpoints with the interactive Swagger UI. Test requests and view response schemas in real-time.</p>
                    <a href="/docs">Open Swagger UI →</a>
                </div>
                
                <div class="card">
                    <h3>Sample Data</h3>
                    <p>Access sample JSON data through our REST API. Perfect for testing and development purposes.</p>
                    <a href="/api/data">Get Data →</a>
                </div>
            </div>
        </main>
    </body>
    </html>
    """


@app.get("/health")
def health():
    return {"status": "ok"}
