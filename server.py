#!/usr/bin/env python3
"""
YouTube Video Downloader Server (FastAPI)
Run this server, then use the Chrome extension to download videos directly
"""

import subprocess
import sys
import os
from contextlib import asynccontextmanager


# Note: Dependencies are installed via requirements.txt on Render

from fastapi import FastAPI, BackgroundTasks, Query
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import yt_dlp

# Default download folder
DOWNLOAD_FOLDER = os.path.expanduser("~/Downloads/YouTube")

# Cookie file path - export from browser and place here
COOKIE_FILE = os.path.join(os.path.dirname(__file__), "cookies.txt")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    print("=" * 50)
    print("   🎥 YouTube Downloader Server (FastAPI) 🎥")
    print("=" * 50)
    print(f"\n✅ Server running at: http://localhost:8765")
    print(f"📁 Downloads will be saved to: {DOWNLOAD_FOLDER}")
    print(f"📚 API Docs: http://localhost:8765/docs")
    print("\n💡 Keep this running while using the Chrome extension")
    print("   Press Ctrl+C to stop\n")
    print("-" * 50)
    yield
    print("\n\n👋 Server stopped. Goodbye!")


app = FastAPI(
    title="YouTube Downloader API",
    description="Download YouTube videos via Chrome extension",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware for Chrome extension
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_quality_format(quality: str) -> str:
    """Get the format string for the desired quality"""
    quality_formats = {
        "2160": "bestvideo[height<=2160][ext=mp4]+bestaudio[ext=m4a]/best[height<=2160][ext=mp4]/best",
        "1080": "bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/best[height<=1080][ext=mp4]/best",
        "720": "bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/best[height<=720][ext=mp4]/best",
        "480": "bestvideo[height<=480][ext=mp4]+bestaudio[ext=m4a]/best[height<=480][ext=mp4]/best",
    }
    return quality_formats.get(quality, quality_formats["1080"])


def do_download(url: str, quality: str):
    """Background task to download video"""
    os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

    ydl_opts = {
        "format": get_quality_format(quality),
        "outtmpl": f"{DOWNLOAD_FOLDER}/%(title)s_%(height)sp.%(ext)s",
        "merge_output_format": "mp4",
        "quiet": False,
        "no_warnings": False,
        "noplaylist": True,
    }

    # Add cookies if file exists
    if os.path.exists(COOKIE_FILE):
        ydl_opts["cookiefile"] = COOKIE_FILE
        print(f"🍪 Using cookies from: {COOKIE_FILE}")
    else:
        print(
            f"⚠️  No cookies file found. Create {COOKIE_FILE} for better compatibility."
        )

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            print(f"\n✅ Downloaded: {info.get('title', 'Unknown')}")
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")


@app.get("/")
async def root():
    """Root endpoint - Health check"""
    return {
        "success": True,
        "message": "🎥 YouTube Downloader API is running!",
        "endpoints": {
            "/status": "Check server status",
            "/info": "Get video info",
            "/download": "Download video",
        },
    }


@app.get("/status")
async def get_status():
    """Check if server is running"""
    return {
        "success": True,
        "message": "Server is running",
        "download_folder": DOWNLOAD_FOLDER,
    }


@app.get("/info")
async def get_video_info(url: str = Query(..., description="YouTube video URL")):
    """Get video information without downloading"""
    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)

            # Get available formats
            formats = []
            for f in info.get("formats", []):
                if f.get("height") and f.get("ext") == "mp4":
                    formats.append(
                        {
                            "height": f.get("height"),
                            "format_id": f.get("format_id"),
                        }
                    )

            return {
                "success": True,
                "title": info.get("title", "Unknown"),
                "channel": info.get("channel", "Unknown"),
                "duration": info.get("duration", 0),
                "thumbnail": info.get("thumbnail", ""),
                "formats": formats,
            }
    except Exception as e:
        return {"success": False, "message": str(e)}


@app.get("/download")
async def download_video(
    background_tasks: BackgroundTasks,
    url: str = Query(..., description="YouTube video URL"),
    quality: str = Query("1080", description="Video quality: 2160, 1080, 720, 480"),
):
    """Start downloading a YouTube video"""
    # Add download task to background
    background_tasks.add_task(do_download, url, quality)

    return {
        "success": True,
        "message": "Download started! Check your Downloads/YouTube folder.",
    }


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8765))
    uvicorn.run(app, host="0.0.0.0", port=port)
