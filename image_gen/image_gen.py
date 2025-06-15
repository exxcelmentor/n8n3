import os
import sys
import requests
from dotenv import load_dotenv
import fal_client

def safe_print(message):
    try:
        print(message)
    except UnicodeEncodeError:
        print(message.encode('ascii', errors='replace').decode('ascii'))

# Load environment variables
load_dotenv()
api_key = os.getenv("FAL_KEY")

if not api_key:
    safe_print("[!] FAL_KEY not found in .env")
    exit(1)

# Validate inputs
if len(sys.argv) < 3:
    safe_print("Usage: python image_gen.py \"prompt\" \"row_id\"")
    exit(1)

prompt, row_id = sys.argv[1], sys.argv[2]
output_dir = os.path.join("..", "output", "images")
os.makedirs(output_dir, exist_ok=True)
image_path = os.path.join(output_dir, f"{row_id}.png")

try:
    # Submit to FAL
    handler = fal_client.submit(
    "fal-ai/flux",
    arguments={"prompt": prompt, "image_size": "landscape_4_3", "num_images": 1}
)
    result = handler.get()
    image_url = result['images'][0]['url']

    # Download image
    img_data = requests.get(image_url, timeout=60).content
    with open(image_path, "wb") as f:
        f.write(img_data)

    # Check if image saved
    if not os.path.exists(image_path) or os.path.getsize(image_path) == 0:
        raise RuntimeError("Image save failed")

    safe_print(f"[✓] Image saved to: {image_path}")

except Exception as e:
    safe_print(f"[!] Error: {e}")
    if os.path.exists(image_path):
        os.remove(image_path)
    exit(1)
