from yt_dlp import YoutubeDL
import os


def get_video_info(url):
    ydl_opts = {"quiet": True}
    with YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)

    # Get thumbnail
    thumbnail = info.get("thumbnail")

    # Get title
    title = info.get("title")

    # Get available formats (video+audio)
    formats = []
    for f in info["formats"]:
        if f.get("ext") == "mp4":
            formats.append(
                {
                    "format_id": f["format_id"],
                    "quality": f.get("quality_label"),
                    "fps": f.get("fps"),
                    "filesize": f.get("filesize"),
                }
            )

    return title, thumbnail, formats


def download_video(url, format_id, output_path):
    # Ensure directory exists
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

    ydl_opts = {
        "outtmpl": output_path,
        "format": format_id,  # download selected format
        "merge_output_format": "mp4",
    }

    try:
        with YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        print(f"Video downloaded to {output_path}")
    except Exception as e:
        print(f"Download failed: {e}")


if __name__ == "__main__":
    video_url = input("Enter the YouTube video URL: ")

    title, thumbnail, formats = get_video_info(video_url)
    print(f"\nTitle: {title}")
    print(f"Thumbnail URL: {thumbnail}\n")

    print("Available formats:")
    for f in formats:
        print(
            f"Format ID: {f['format_id']}, Quality: {f['quality']}, FPS: {f.get('fps', 'N/A')}, Size: {f.get('filesize', 'N/A')}"
        )

    selected_format = input("\nEnter the format ID you want to download: ")
    output_file = input("Enter the output file path (e.g., ./video.mp4): ")

    download_video(video_url, selected_format, output_file)
