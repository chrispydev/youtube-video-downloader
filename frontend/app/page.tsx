"use client";

import Image from "next/image";
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
  size?: string;
  formats: VideoFormat[];
  // Optional subtitle metadata returned by the backend
  subtitle_languages?: string[];
  subtitles?: Record<string, any>;
  automatic_captions?: Record<string, any>;
}

export default function Home() {
  const [url, setUrl] = useState("");
  const [info, setInfo] = useState<VideoInfo | null>(null);
  const [selectedFormat, setSelectedFormat] = useState("");
  // Subtitle selection & available languages
  const [selectedSubtitleLang, setSelectedSubtitleLang] = useState<
    string | null
  >(null);
  const [subtitleLanguages, setSubtitleLanguages] = useState<string[]>([]);
  const [status, setStatus] = useState("");
  const [loadingInfo, setLoadingInfo] = useState(false);
  const [downloading, setDownloading] = useState(false);

  // const BACKEND = "https://youtube-video-downloader-bfgo.onrender.com";
  const BACKEND = "http://127.0.0.1:8000";

  // ---------------------------
  // Fetch video info
  // ---------------------------
  const fetchInfo = async () => {
    console.log("Fetching info for URL:", url);
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
      console.log(data);

      if (data.error) {
        setStatus(`❌ ${data.error}`);
        setLoadingInfo(false);
        return;
      }

      // Deduplicate formats client-side and prefer formats that include audio.
      // We dedupe by ext + resolution and keep the entry that either has audio (preferred)
      // or the larger filesize as a fallback.
      const rawFormats = Array.isArray(data.formats) ? data.formats : [];
      const seen = new Map<string, any>();
      const deduped: any[] = [];
      for (const f of rawFormats) {
        const key = `${f.ext}|${f.resolution || f.format_note || "N/A"}`;
        if (!seen.has(key)) {
          seen.set(key, f);
          deduped.push(f);
        } else {
          const existing = seen.get(key);
          const existingSize = existing?.filesize || 0;
          const newSize = f?.filesize || 0;
          // prefer the one with audio; otherwise prefer larger filesize
          const preferNew =
            (!!f.has_audio && !existing?.has_audio) ||
            (newSize > existingSize &&
              (!!f.has_audio || !existing?.has_audio));
          if (preferNew) {
            seen.set(key, f);
            const idx = deduped.findIndex(
              (x) =>
                x.ext === existing.ext &&
                (x.resolution || x.format_note || "N/A") ===
                (existing.resolution ||
                  existing.format_note ||
                  "N/A"),
            );
            if (idx !== -1) deduped[idx] = f;
          }
        }
      }
      data.formats = deduped;

      // Pick a sensible default selected format:
      // 1) prefer mp4 that has audio
      // 2) otherwise any format that has audio
      // 3) otherwise the first available format
      let defaultFormat = "";
      if (Array.isArray(data.formats) && data.formats.length > 0) {
        const mp4WithAudio = data.formats.find(
          (x: any) => x.ext === "mp4" && x.has_audio,
        );
        const anyWithAudio = data.formats.find((x: any) => x.has_audio);
        defaultFormat =
          (mp4WithAudio && mp4WithAudio.format_id) ||
          (anyWithAudio && anyWithAudio.format_id) ||
          data.formats[0].format_id;
      }

      setInfo({ ...(data as any), formats: data.formats });
      setStatus("Video info loaded!");
      if (defaultFormat) setSelectedFormat(defaultFormat);

      // Populate subtitle language choices if provided by backend
      if (
        Array.isArray(data.subtitle_languages) &&
        data.subtitle_languages.length > 0
      ) {
        setSubtitleLanguages(data.subtitle_languages);
        // Prefer English when available
        setSelectedSubtitleLang(
          data.subtitle_languages.includes("en")
            ? "en"
            : data.subtitle_languages[0],
        );
      } else {
        setSubtitleLanguages([]);
        setSelectedSubtitleLang(null);
      }
    } catch (error) {
      setStatus(`❌ Failed to fetch video info., ${error}`);
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
    const downloadVideo = {
      url: url,
      format_id: selectedFormat,
      subtitle_lang: selectedSubtitleLang,
    }
    console.log(downloadVideo)

    try {
      const res = await fetch(`${BACKEND}/download`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          url,
          format_id: selectedFormat,
          subtitle_lang: "en",
          // subtitle_lang: selectedSubtitleLang,
        }),
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
      setStatus(`❌ Error during download., ${error}`);
    }

    setDownloading(false);
  };

  return (
    <div className="min-h-screen flex flex-col items-center p-6 bg-linear-to-br from-gray-900 via-black to-gray-800 text-white">
      <h1 className="text-4xl font-extrabold mb-6 text-center bg-clip-text text-transparent bg-linear-to-br from-purple-500 to-pink-500">
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
          className="w-full mt-4 p-4 bg-linear-to-r from-blue-600 to-purple-600 hover:opacity-90 rounded-xl text-lg font-semibold transition disabled:opacity-50"
        >
          {loadingInfo ? "Fetching Info…" : "Get Video Info"}
        </button>
      </div>

      {/* Video Info */}
      {info && (
        <div className="mt-8 w-full max-w-xl bg-gray-800/60 p-6 rounded-2xl border border-gray-700 shadow-xl">
          <Image
            src={info.thumbnail}
            width={300}
            height={300}
            alt="thumbnail"
            className="rounded-xl mb-4 w-full shadow-lg"
          />
          <h2 className="text-2xl font-bold">{info.title}</h2>
          <p className="text-gray-400 mt-1">
            Duration: {info.duration}s | Uploader:{" "}
            {info.uploader || "N/A"}
          </p>

          {/* Quality Selection */}
          {info.formats.length > 0 && (
            <div className="mt-4">
              <label className="text-gray-300 font-medium">
                Select Quality
              </label>
              <select
                value={selectedFormat}
                onChange={(e) =>
                  setSelectedFormat(e.target.value)
                }
                className="w-full mt-2 p-3 bg-gray-900 border border-gray-700 rounded-xl focus:ring-2 focus:ring-purple-500 outline-none"
              >
                {info.formats.map((f) => (
                  <option
                    key={f.format_id}
                    value={f.format_id}
                  >
                    {f.resolution} ({f.ext}) size:{" "}
                    {f.filesize}
                  </option>
                ))}
              </select>

              {/* Subtitle language selection (if available) */}
              {subtitleLanguages.length > 0 && (
                <div className="mt-4">
                  <label className="text-gray-300 font-medium">
                    Subtitle Language
                  </label>
                  <select
                    value={selectedSubtitleLang || ""}
                    onChange={(e) =>
                      setSelectedSubtitleLang(
                        e.target.value || null,
                      )
                    }
                    className="w-full mt-2 p-3 bg-gray-900 border border-gray-700 rounded-xl focus:ring-2 focus:ring-purple-500 outline-none"
                  >
                    <option value="">(none)</option>
                    {subtitleLanguages.map((lang) => (
                      <option key={lang} value={lang}>
                        {lang}
                      </option>
                    ))}
                  </select>
                </div>
              )}
            </div>
          )}

          <button
            onClick={downloadVideo}
            disabled={downloading}
            className="w-full mt-6 p-4 bg-linear-to-r from-green-600 to-emerald-600 hover:opacity-90 rounded-xl text-lg font-semibold transition disabled:opacity-50"
          >
            {downloading ? "Downloading…" : "Download Video"}
          </button>
        </div>
      )}

      {/* Status Message */}
      {status && (
        <div className="mt-4 text-lg font-semibold text-yellow-300">
          {status}
        </div>
      )}
    </div>
  );
}
