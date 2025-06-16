"""Combined pipeline script that processes the first pending row from the
Google Sheet and generates the corresponding image, audio and video.
This replaces the previous multi-venv workflow.
"""

from __future__ import annotations

import os
from pathlib import Path
import requests
import gspread
import fal_client
from dotenv import load_dotenv
from TTS.api import TTS
from moviepy.audio.io.AudioFileClip import AudioFileClip
from moviepy.video.VideoClip import ImageClip, TextClip
from moviepy.video.compositing.CompositeVideoClip import CompositeVideoClip
from moviepy.video.fx.resize import resize
from moviepy.video.fx.fadein import fadein
from moviepy.video.fx.fadeout import fadeout
from PIL import Image
import numpy as np

# os.environ["IMAGEMAGICK_BINARY"] = "/Users/anilvyas/Downloads/ImageMagick-7.0.10/magick"
os.environ["IMAGETO_FEMPEG_EXE"] = r"/Users/anilvyas/ImageMagick-7.0.10/bin/convert"

BASE_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = BASE_DIR / "output"


def safe_print(message: str) -> None:
    """Print helper that falls back to ASCII when needed."""
    try:
        print(message)
    except UnicodeEncodeError:
        print(message.encode("ascii", errors="replace").decode("ascii"))


def fetch_pending_row():
    """Return the first pending row from the Google Sheet."""
    load_dotenv(BASE_DIR / ".env")
    sheet_id = os.getenv("GOOGLE_SHEET_ID")
    if not sheet_id:
        raise ValueError("GOOGLE_SHEET_ID missing from .env")

    gc = gspread.service_account(filename=str(BASE_DIR / "creds" / "service_account.json"))
    worksheet = gc.open_by_key(sheet_id).worksheet("Challenge30")

    records = worksheet.get_all_records()
    for idx, row in enumerate(records, start=2):
        if row.get("video_status", "").strip().lower() == "pending":
            return row, idx, worksheet
    return None, None, worksheet


def generate_image(prompt: str, row_id: str) -> Path:
    """Generate an image using fal-client and return the file path."""
    load_dotenv(BASE_DIR / ".env")
    api_key = os.getenv("FAL_KEY")
    if not api_key:
        raise RuntimeError("FAL_KEY not found in .env")

    handler = fal_client.submit(
        "fal-ai/flux",
        arguments={"prompt": prompt, "image_size": "landscape_4_3", "num_images": 1},
    )
    result = handler.get()
    image_url = result["images"][0]["url"]

    img_data = requests.get(image_url, timeout=60).content
    out_dir = OUTPUT_DIR / "images"
    out_dir.mkdir(parents=True, exist_ok=True)
    image_path = out_dir / f"{row_id}.png"
    with open(image_path, "wb") as f:
        f.write(img_data)
    return image_path


def generate_audio(text: str, row_id: str) -> Path:
    """Generate speech audio from text."""
    out_dir = OUTPUT_DIR / "audio"
    out_dir.mkdir(parents=True, exist_ok=True)
    output_file = out_dir / f"{row_id}.wav"

    tts = TTS(model_name="tts_models/en/ljspeech/tacotron2-DDC", progress_bar=True, gpu=False)
    tts.tts_to_file(text=text, file_path=str(output_file))
    return output_file


def generate_video(row_id: str, caption: str | None = None) -> Path:
    """Create a simple video from the generated image and audio."""
    img = OUTPUT_DIR / "images" / f"{row_id}.png"
    aud = OUTPUT_DIR / "audio" / f"{row_id}.wav"
    out = OUTPUT_DIR / "videos" / f"{row_id}.mp4"

    if not img.exists() or not aud.exists():
        missing = "\n".join(str(p) for p in (img, aud) if not p.exists())
        raise FileNotFoundError(f"Missing:\n{missing}")

    audio = AudioFileClip(str(aud))
    duration = audio.duration * 1.05

    # Create a custom resize function that uses LANCZOS instead of ANTIALIAS
    def custom_resize(clip, factor_func):
        def resize_frame(get_frame, t):
            frame = get_frame(t)
            factor = factor_func(t)
            new_size = (int(frame.shape[1] * factor), int(frame.shape[0] * factor))
            return np.array(Image.fromarray(frame).resize(new_size, Image.Resampling.LANCZOS))
        return clip.fl(lambda gf, t: resize_frame(gf, t))

    image = (
        ImageClip(str(img))
        .set_duration(duration)
        .set_audio(audio)
        .fx(custom_resize, lambda t: 1 + 0.05 * (t / duration))
        .fx(fadein, 0.5)
        .fx(fadeout, 0.5)
        .set_position("center")
    )

    clips = [image]
    if caption:
        txt = (
            TextClip(
                caption,
                font="Arial",  # Using a more generic font name
                fontsize=48,
                color="white",
                bg_color="black",
                stroke_color="white",
                stroke_width=2,
                method="caption",
                size=(int(image.w * 0.8), None),
            )
            .set_duration(duration)
            .set_position(("center", "bottom"))
            .fx(fadein, 0.5)
            .fx(fadeout, 0.5)
        )
        clips.append(txt)

    video = CompositeVideoClip(clips, size=image.size)
    out.parent.mkdir(parents=True, exist_ok=True)
    video.write_videofile(str(out), fps=24, codec="libx264", audio_codec="aac", threads=4, verbose=True)
    return out


def update_sheet(worksheet, row_index: int, video_path: str) -> None:
    """Update Google Sheet status and link."""
    status_col = worksheet.find("video_status").col
    link_col = worksheet.find("video link").col
    worksheet.update_cell(row_index, status_col, "done")
    worksheet.update_cell(row_index, link_col, video_path)


def main() -> None:
    row, row_idx, worksheet = fetch_pending_row()
    if not row:
        safe_print("No pending rows found.")
        return

    safe_print(f"Processing row ID: {row['id']}")
    generate_image(row["image_prompt"], row["id"])
    generate_audio(row["audio_script"], row["id"])
    video_path = generate_video(row["id"], caption=row["audio_script"])
    update_sheet(worksheet, row_idx, str(video_path))
    safe_print(f"Pipeline completed for {row['id']}")


if __name__ == "__main__":
    main()

