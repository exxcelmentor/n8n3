import os
import gspread
from dotenv import load_dotenv
import subprocess

# Load environment variables
load_dotenv(dotenv_path="../image_gen/.env")
sheet_id = os.getenv("GOOGLE_SHEET_ID")
if not sheet_id:
    raise ValueError("GOOGLE_SHEET_ID missing from .env!")

# Authenticate with Google Sheets
gc = gspread.service_account(filename="../creds/service_account.json")
worksheet = gc.open_by_key(sheet_id).worksheet("Challenge30")

# Find first pending row
records = worksheet.get_all_records()
pending_index = None
pending_row = None
for i, row in enumerate(records, start=2):
    if row.get("video_status", "").strip().lower() == "pending":
        pending_index = i
        pending_row = row
        break

if not pending_row:
    print("No pending rows found.")
    exit()

print("Pending row:", pending_row)

def run_subprocess(venv_path, script_path, *args):
    cmd = [
        os.path.join(venv_path, "Scripts", "python.exe"),
        script_path,
        *args
    ]
    try:
        result = subprocess.run(
            cmd,
            check=True,
            capture_output=True,
            text=True
        )
        print(result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr)
        return True, result.stdout
    except subprocess.CalledProcessError as e:
        print("[!] Process failed:", e.stderr)
        return False, e.stdout or ""

# 1. Image
print(f"\n[*] Generating image for ID: {pending_row['id']}")
ok, _ = run_subprocess("../image_gen/venv", "../image_gen/image_gen.py",
                       pending_row["image_prompt"], pending_row["id"])
if not ok: exit(1)

# 2. Audio
print(f"\n[*] Generating audio for ID: {pending_row['id']}")
ok, _ = run_subprocess("../tts_gen/venv", "../tts_gen/tts_gen.py",
                       pending_row["audio_script"], pending_row["id"])
if not ok: exit(1)

# 3. Video
print(f"\n[*] Generating video for ID: {pending_row['id']}")
ok, stdout = run_subprocess("../video_gen/venv", "../video_gen/video_gen.py",
                            pending_row["id"], pending_row["audio_script"])
if not ok: exit(1)

# Extract video path from last non-empty line of stdout
video_path = stdout.strip().splitlines()[-1]
print(f"📹 Video generated at: {video_path}")

# ✅ Update status and link in Google Sheet
status_col = worksheet.find("video_status").col
link_col = worksheet.find("video link").col
worksheet.update_cell(pending_index, status_col, "done")
worksheet.update_cell(pending_index, link_col, video_path)

print(f"[OK] Completed pipeline for ID {pending_row['id']}")
