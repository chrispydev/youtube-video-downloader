# 📥 Python YouTube Downloader

A lightweight and reliable **Python-based YouTube downloader** using **yt-dlp**.
Supports fetching video metadata, available qualities, thumbnails, and downloading selected video formats.

---

## 🚀 Features

* Fetch video **title** and **thumbnail**
* List all **available formats and qualities**
* Download video in chosen **quality**
* Merges video and audio automatically using **ffmpeg**

---

## ▶️ Usage

```bash
python main.py
```

* Enter the **YouTube video URL**
* Choose a **format ID** from the available options
* Enter the **output file path**

---

## ⚡ Requirements

* Python 3.10+
* [yt-dlp](https://pypi.org/project/yt-dlp/) (`pip install yt-dlp`)
* [ffmpeg](https://ffmpeg.org/) installed and in PATH

---

## 🧹 .gitignore Example

```
venv/
downloads/
__pycache__/
```

---

## 🏷 License

MIT License
