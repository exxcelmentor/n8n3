import io
import os
import sys
from pathlib import Path
from TTS.api import TTS

def generate_speech(text, output_file):
    try:
        print("[*] Initializing TTS...")
        tts = TTS(model_name="tts_models/en/ljspeech/tacotron2-DDC", progress_bar=True, gpu=False)
        
        print("[*] Generating speech...")
        tts.tts_to_file(text=text, file_path=output_file)
        
        print(f"[+] Success! Output saved to: {os.path.abspath(output_file)}")
        return True
    except Exception as e:
        print(f"[!] Error: {str(e)}")
        return False

if __name__ == "__main__":
    # Configure output directory
    output_dir = Path("../output/audio")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Handle CLI arguments
    if len(sys.argv) < 3:
        print("Usage: python tts_gen.py \"text_to_speak\" \"row_id\"")
        sys.exit(1)
    
    text = sys.argv[1]
    row_id = sys.argv[2]
    output_file = output_dir / f"{row_id}.wav"

    if generate_speech(text, output_file):
        print(f"[OK] Audio saved to {output_file}")
    else:
        sys.exit(1)