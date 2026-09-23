import sys
from pathlib import Path
import httpx

CURRENT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = CURRENT_DIR.parent
BACKEND_DIR = PROJECT_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.config import settings

def main():
    headers = {
        "Authorization": f"Bearer {settings.NVIDIA_API_KEY}",
        "Content-Type": "application/json",
    }
    url = f"{settings.NVIDIA_BASE_URL}/chat/completions"
    payload = {
        "model": settings.NVIDIA_MODEL,
        "messages": [
            {"role": "user", "content": "Hello, answer in 5 words."}
        ],
        "max_tokens": 50,
    }
    print(f"Testing model: {settings.NVIDIA_MODEL} at {url}...")
    with httpx.Client(timeout=15.0) as client:
        r = client.post(url, headers=headers, json=payload)
        print("Status:", r.status_code)
        print("Response:", r.text[:300])

if __name__ == "__main__":
    main()
