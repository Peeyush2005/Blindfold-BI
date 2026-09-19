"""
Probe Models Script.
Evaluates connectivity, latency, and capabilities across NVIDIA NIM models
and verifies local degraded fallback.
"""

import sys
import time
import asyncio
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import settings
from app.core.llm_client import llm_client, TokenBucket


async def probe():
    print("=" * 60)
    print(f"Blindfold BI — NVIDIA NIM Model Probe")
    print(f"Base URL: {settings.NVIDIA_BASE_URL}")
    print(f"Primary Model: {settings.NVIDIA_MODEL}")
    print(f"API Key Configured: {bool(settings.NVIDIA_API_KEY)}")
    print("=" * 60)

    models_to_test = [
        settings.NVIDIA_MODEL,
    ]

    if not llm_client.client:
        print("[!] No AsyncOpenAI client initialized (check NVIDIA_API_KEY in .env).")
        print("[i] Testing local deterministic fallback synthesizer...")
        sample_tool_data = {
            "template": "Pipeline has [[F1]] across [[F2]] open deals.",
            "facts": [
                {"id": "F1", "label": "Pipeline Value", "display": "₹68.82 Cr", "value": 688152293.17},
                {"id": "F2", "label": "Open Deals", "display": "49", "value": 49},
            ],
            "dq": [],
        }
        res = llm_client._synthesize_local("pipeline_summary", sample_tool_data)
        print("[+] Local synthesizer verified successfully:\n", res[:180], "...\n")
        return

    for model in models_to_test:
        print(f"\nProbing {model}...")
        t0 = time.time()
        try:
            resp = await asyncio.wait_for(
                llm_client.client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "user", "content": "Ping. Respond strictly with PONG."}
                    ],
                    max_tokens=10,
                    temperature=0.0,
                ),
                timeout=10.0,
            )
            lat = round((time.time() - t0) * 1000, 2)
            content = resp.choices[0].message.content.strip()
            print(f"  [SUCCESS] Latency: {lat}ms | Response: {content}")
        except asyncio.TimeoutError:
            print(f"  [TIMEOUT] Model {model} exceeded 10.0s timeout.")
        except Exception as e:
            print(f"  [FAILED] Model {model} returned error: {e}")

    print("\n" + "=" * 60)
    print("Testing Rate Limiter TokenBucket...")
    bucket = TokenBucket(rate=1.0, capacity=2.0)
    assert await bucket.acquire(1.0)
    assert await bucket.acquire(1.0)
    print("  [SUCCESS] TokenBucket rate limiter verified.")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(probe())
