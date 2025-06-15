import os
import gspread
from dotenv import load_dotenv
import subprocess

# Load environment variables
load_dotenv(dotenv_path="../.env")
sheet_id = os.getenv("GOOGLE_SHEET_ID")

if not sheet_id:
    raise ValueError("GOOGLE_SHEET_ID missing from .env!")

# Authenticate with Google Sheets
gc = gspread.service_account(filename="../creds/service_account.json")
worksheet = gc.open_by_key(sheet_id).worksheet("Challenge30")

# Get all rows (including headers) and find the first 'pending' row with index
records = worksheet.get_all_records()
pending_index = None
pending_row = None

for i, row in enumerate(records, start=2):  # +2 to account for 0-index + header row
    if row.get("video_status", "").strip().lower() == "pending":
        pending_index = i
        pending_row = row
        break

if not pending_row:
    print("No pending rows found.")
    exit()

print("Pending row found:")
for key, value in pending_row.items():
    print(f"{key}: {value}")

# --- Pipeline Execution ---
def run_subprocess(venv_path, script_path, *args):
    try:
        result = subprocess.run(
            [
                os.path.join(venv_path, "Scripts", "python.exe"),
                script_path,
                *args
            ],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding='utf-8',
            errors='replace'
        )
        print(result.stdout)
        if result.stderr:
            print(f"STDERR: {result.stderr}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"[!] Process failed: {e.stderr}")
        return False

# 1. Image Generation
print(f"\n[*] Generating image for ID: {pending_row['id']}")
if not run_subprocess(
    r"..\image_gen\venv",
    r"..\image_gen\image_gen.py",
    pending_row["image_prompt"],
    pending_row["id"]
):
    exit(1)

# 2. Audio Generation
print(f"\n[*] Generating audio for ID: {pending_row['id']}")
if not run_subprocess(
    r"..\tts_gen\venv",
    r"..\tts_gen\tts_gen.py",
    pending_row["audio_script"],
    pending_row["id"]
):
    exit(1)

# 3. Video Assembly
print(f"\n[*] Generating video for ID: {pending_row['id']}")
if not run_subprocess(
    r"..\video_gen\venv",
    r"..\video_gen\video_gen.py",
    pending_row["id"],
    pending_row["audio_script"]
):
    exit(1)

# ✅ Update video_status in Google Sheet
print("\n[*] Updating Google Sheet status to 'done'...")
status_col = worksheet.find("video_status").col
worksheet.update_cell(pending_index, status_col, "done")
print(f"[OK] Pipeline completed for {pending_row['id']}")
