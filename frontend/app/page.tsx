"use client";

import React, { useState } from "react";

interface VideoFormat {
  format_id: string;
  ext: string;
  resolution: string;
  filesize?: number;
  format_note?: string;
}

interface VideoInfo {
  title: string;
  thumbnail: string;
  duration: number;
  uploader?: string;
  description?: string;
  formats: VideoFormat[];
}

export default function Home() {
  const [url, setUrl] = useState("");
  const [info, setInfo] = useState<VideoInfo | null>(null);
  const [selectedFormat, setSelectedFormat] = useState("");
  const [status, setStatus] = useState("");
  const [loadingInfo, setLoadingInfo] = useState(false);
  const [downloading, setDownloading] = useState(false);

  const BACKEND = "http://localhost:8000";

  // ---------------------------
  // Fetch video info
  // ---------------------------
  const fetchInfo = async () => {
    if (!url.trim()) return;

    setLoadingInfo(true);
    setStatus("Fetching video info...");
    setInfo(null);

    try {
      const res = await fetch(`${BACKEND}/info`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url }),
      });

      const data = await res.json();

      if (data.error) {
        setStatus(`❌ ${data.error}`);
        setLoadingInfo(false);
        return;
      }

      setInfo(data);
      setStatus("Video info loaded!");
      if (data.formats && data.formats.length > 0) {
        setSelectedFormat(data.formats[0].format_id);
      }
    } catch (error) {
      setStatus("❌ Failed to fetch video info.");
    }

    setLoadingInfo(false);
  };

  // ---------------------------
  // Download video
  // ---------------------------
  const downloadVideo = async () => {
    if (!info || !selectedFormat) {
      alert("Select a format first!");
      return;
    }

    setDownloading(true);
    setStatus("Downloading… Please wait.");

    try {
      const res = await fetch(`${BACKEND}/download`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url, format_id: selectedFormat }),
      });

      if (!res.ok) {
        setStatus("❌ Download failed.");
        setDownloading(false);
        return;
      }

      const blob = await res.blob();
      const downloadUrl = window.URL.createObjectURL(blob);

      const a = document.createElement("a");
      a.href = downloadUrl;
      a.download = info.title.replace(/[^\w\s-]/g, "") + ".mp4";
      a.click();

      setStatus("✅ Download complete!");
    } catch (error) {
      setStatus("❌ Error during download.");
    }

    setDownloading(false);
  };

  return (
    <div className="min-h-screen flex flex-col items-center p-6 bg-gradient-to-br from-gray-900 via-black to-gray-800 text-white">
      <h1 className="text-4xl font-extrabold mb-6 text-center bg-clip-text text-transparent bg-gradient-to-r from-purple-500 to-pink-500">
        Premium YouTube Downloader
      </h1>

      {/* Input Section */}
      <div className="w-full max-w-xl bg-gray-900/60 backdrop-blur-xl p-6 rounded-3xl shadow-2xl border border-gray-800">
        <input
          type="text"
          placeholder="Paste YouTube URL here..."
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          className="w-full p-4 rounded-xl bg-gray-800 border border-gray-700 focus:ring-2 focus:ring-purple-500 outline-none text-lg"
        />
        <button
          onClick={fetchInfo}
          disabled={loadingInfo || !url}
          className="w-full mt-4 p-4 bg-gradient-to-r from-blue-600 to-purple-600 hover:opacity-90 rounded-xl text-lg font-semibold transition disabled:opacity-50"
        >
          {loadingInfo ? "Fetching Info…" : "Get Video Info"}
        </button>
      </div>

      {/* Video Info */}
      {info && (
        <div className="mt-8 w-full max-w-xl bg-gray-800/60 p-6 rounded-2xl border border-gray-700 shadow-xl">
          <img
            src={info.thumbnail}
            alt="thumbnail"
            className="rounded-xl mb-4 w-full shadow-lg"
          />
          <h2 className="text-2xl font-bold">{info.title}</h2>
          <p className="text-gray-400 mt-1">
            Duration: {info.duration}s | Uploader: {info.uploader || "N/A"}
          </p>

          {/* Quality Selection */}
          {info.formats.length > 0 && (
            <div className="mt-4">
              <label className="text-gray-300 font-medium">Select Quality</label>
              <select
                value={selectedFormat}
                onChange={(e) => setSelectedFormat(e.target.value)}
                className="w-full mt-2 p-3 bg-gray-900 border border-gray-700 rounded-xl focus:ring-2 focus:ring-purple-500 outline-none"
              >
                {info.formats.map((f) => (
                  <option key={f.format_id} value={f.format_id}>
                    {f.resolution} ({f.ext})
                  </option>
                ))}
              </select>
            </div>
          )}

          <button
            onClick={downloadVideo}
            disabled={downloading}
            className="w-full mt-6 p-4 bg-gradient-to-r from-green-600 to-emerald-600 hover:opacity-90 rounded-xl text-lg font-semibold transition disabled:opacity-50"
          >
            {downloading ? "Downloading…" : "Download Video"}
          </button>
        </div>
      )}

      {/* Status Message */}
      {status && (
        <div className="mt-4 text-lg font-semibold text-yellow-300">{status}</div>
      )}
    </div>
  );
}

