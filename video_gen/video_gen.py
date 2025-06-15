import sys, os
from pathlib import Path
import moviepy.config as mpc

# 1️⃣ Configure ImageMagick & FFmpeg early
mpc.IMAGEMAGICK_BINARY = r"C:\Program Files\ImageMagick-6.9.13-Q16-HDRI\convert.exe"
os.environ["IMAGEIO_FFMPEG_EXE"] = r"C:\full\path\to\ffmpeg.exe"

from moviepy.audio.io.AudioFileClip import AudioFileClip
from moviepy.video.VideoClip import ImageClip, TextClip
from moviepy.video.compositing.CompositeVideoClip import CompositeVideoClip
from moviepy.video.fx.resize import resize
from moviepy.video.fx.fadein import fadein
from moviepy.video.fx.fadeout import fadeout

# Read the caption from the command line
caption = sys.argv[1] if len(sys.argv) > 1 else None

def generate_video(row_id: str, caption: str = None) -> Path:
    base = Path(__file__).resolve().parent.parent
    img = base / "output" / "images" / f"{row_id}.png"
    aud = base / "output" / "audio" / f"{row_id}.wav"
    out = base / "output" / "videos" / f"{row_id}.mp4"

    # Validate file existence
    if not img.exists() or not aud.exists():
        raise FileNotFoundError("Missing:\n" +
                                "\n".join(str(p) for p in (img, aud) if not p.exists()))

    audio = AudioFileClip(str(aud))
    duration = audio.duration * 1.05

    # Create image clip with zoom effect via fx
    image = (ImageClip(str(img))
             .set_duration(duration)
             .set_audio(audio)
             .fx(resize, lambda t: 1 + 0.05 * (t / duration))
             .fx(fadein, 0.5)
             .fx(fadeout, 0.5)
             .set_position("center"))

    clips = [image]

    if caption:
        txt = (TextClip(
                    caption,
                    font="C:/Windows/Fonts/arial.ttf",
                    fontsize=48,
                    color="white",
                    bg_color="black",
                    stroke_color="white",
                    stroke_width=2,
                    method="caption",
                    size=(int(image.w * 0.8), None)
                )
               .set_duration(duration)
               .set_position(("center", "bottom"))
               .fx(fadein, 0.5)
               .fx(fadeout, 0.5))

        clips.append(txt)

    video = CompositeVideoClip(clips, size=image.size)
    out.parent.mkdir(parents=True, exist_ok=True)
    video.write_videofile(
        str(out), fps=24, codec="libx264", audio_codec="aac",
        threads=4, verbose=True
    )

    return out

if __name__ == "__main__":
    print(f"Caption: {caption!r}")
    try:
        result = generate_video("TEST_001", caption=caption)
        print(f"OK Video created at: {result}")
    except Exception as e:
        print("NotOK Error:", e)
