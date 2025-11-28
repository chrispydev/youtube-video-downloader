"use client";

import { useState } from "react";

interface Format {
  format_id: string;
  ext: string;
  resolution: string | null;
  filesize: number | null;
  format_note: string | null;
}

interface DownloadHistoryItem {
  title: string;
  format: string;
  url: string;
}

export default function Home() {
  const [url, setUrl] = useState("");
  const [loadingInfo, setLoadingInfo] = useState(false);
  const [info, setInfo] = useState<any>(null);
  const [selectedFormat, setSelectedFormat] = useState<string>("");
  const [downloading, setDownloading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [history, setHistory] = useState<DownloadHistoryItem[]>([]);

  // Fetch video info
  const fetchInfo = async () => {
    if (!url) return;
    setLoadingInfo(true);
    setInfo(null);

    try {
      const res = await fetch("http://localhost:8000/info", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url }),
      });
      const data = await res.json();
      setInfo(data);
    } catch (err) {
      console.error(err);
      alert("Failed to fetch video info.");
    }
    setLoadingInfo(false);
  };

  // Download video with progress
  const download = async () => {
    if (!selectedFormat) {
      alert("Select a quality");
      return;
    }

    setDownloading(true);
    setProgress(0);

    try {
      const res = await fetch("http://localhost:8000/download", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url, format_id: selectedFormat }),
      });

      const reader = res.body?.getReader();
      const contentLength = res.headers.get("Content-Length");
      const total = contentLength ? parseInt(contentLength) : 0;
      let received = 0;
      const chunks: Uint8Array[] = [];

      if (reader) {
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          if (value) {
            chunks.push(value);
            received += value.length;
            if (total) setProgress(Math.floor((received / total) * 100));
          }
        }
      }

      // Convert chunks to blob
      const blob = new Blob(chunks);
      const blobUrl = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = blobUrl;
      a.download = "video.mp4";
      a.click();

      // Update history
      setHistory([
        ...history,
        { title: info.title, format: selectedFormat, url },
      ]);
    } catch (err) {
      console.error(err);
      alert("Download failed.");
    }

    setDownloading(false);
    setProgress(0);
  };

  return (
    <main className="min-h-screen bg-gradient-to-r from-purple-500 to-indigo-600 flex flex-col items-center p-6">
      <h1 className="text-4xl font-extrabold text-white mb-8 drop-shadow-lg">
        Premium Video Downloader
      </h1>

      <div className="w-full max-w-2xl backdrop-blur-sm bg-white/20 shadow-2xl rounded-2xl p-8 flex flex-col items-center">
        <input
          type="text"
          placeholder="Enter YouTube URL"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          className="w-full border border-white/50 rounded-lg p-4 mb-5 bg-white/30 placeholder-white text-white focus:outline-none focus:ring-2 focus:ring-purple-400 focus:border-transparent"
        />

        <button
          onClick={fetchInfo}
          className="w-full bg-purple-600 hover:bg-purple-700 text-white font-semibold py-3 rounded-lg shadow-md transition transform hover:-translate-y-1 hover:scale-105 mb-6"
        >
          {loadingInfo ? "Fetching..." : "Get Video Info"}
        </button>

        {/* Loading Skeleton */}
        {loadingInfo && (
          <div className="w-full animate-pulse">
            <div className="h-48 bg-white/30 rounded-lg mb-4"></div>
            <div className="h-6 bg-white/30 rounded mb-2"></div>
            <div className="h-6 bg-white/30 rounded mb-2"></div>
            <div className="h-6 bg-white/30 rounded mb-2"></div>
          </div>
        )}

        {/* Video Info Card */}
        {info && (
          <div className="w-full flex flex-col items-center">
            <img
              src={info.thumbnail}
              alt="Thumbnail"
              className="rounded-xl mb-4 shadow-lg max-w-full"
            />
            <h2 className="text-2xl font-bold text-white mb-2 text-center drop-shadow-md">
              {info.title}
            </h2>
            <p className="text-white/80 mb-4">{info.uploader}</p>

            <select
              value={selectedFormat}
              onChange={(e) => setSelectedFormat(e.target.value)}
              className="w-full p-3 rounded-lg mb-4 bg-white/30 text-white border border-white/50 focus:outline-none focus:ring-2 focus:ring-purple-400"
            >
              <option value="">Select Quality</option>
              {info.formats.map((f: Format) => (
                <option key={f.format_id} value={f.format_id}>
                  {f.resolution || "Audio"} — {f.ext.toUpperCase()}{" "}
                  {f.filesize
                    ? `(${(f.filesize / 1024 / 1024).toFixed(1)} MB)`
                    : ""}
                </option>
              ))}
            </select>

            <button
              onClick={download}
              disabled={downloading}
              className={`w-full ${downloading ? "bg-gray-500 cursor-not-allowed" : "bg-green-500 hover:bg-green-600"
                } text-white font-semibold py-3 rounded-lg shadow-md transition transform hover:-translate-y-1 hover:scale-105`}
            >
              {downloading ? `Downloading ${progress}%` : "Download"}
            </button>

            {downloading && (
              <div className="w-full bg-white/30 rounded-full h-3 mt-3 overflow-hidden">
                <div
                  className="bg-green-400 h-3"
                  style={{ width: `${progress}%` }}
                ></div>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Download History */}
      {history.length > 0 && (
        <div className="w-full max-w-2xl mt-8 bg-white/20 backdrop-blur-sm p-6 rounded-2xl shadow-xl">
          <h3 className="text-xl font-bold text-white mb-4">Download History</h3>
          <ul className="space-y-3">
            {history.map((item, idx) => (
              <li
                key={idx}
                className="bg-white/30 p-3 rounded-lg text-white flex justify-between items-center shadow-md"
              >
                <span>{item.title}</span>
                <span className="text-sm">{item.format}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      <p className="mt-8 text-white/70 text-sm text-center">
        Powered by FastAPI & yt-dlp
      </p>
    </main>
  );
}

