import os
import json
import secrets
import requests
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from collections import deque

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load the 100k token library
TOKEN_PATH = os.path.join(os.getcwd(), "tokens.json")
with open(TOKEN_PATH, "r") as f:
    TOKENS = json.load(f)

# The Quantum Buffer
# We store indices here so we don't have to hit the API every 100ms
QUANTUM_BUFFER = deque()

def refill_buffer():
    """
    Fetches a massive block of entropy from LFDR (e.g., 400 bytes).
    Each token needs 4 bytes (for 100k+ range), so this gives us 100 tokens.
    """
    try:
        # Request 400 bytes (100 tokens worth of entropy)
        r = requests.get("https://lfdr.de/qrng_api/qrng?length=400&format=HEX", timeout=2.0)
        if r.status_code == 200:
            raw_hex = r.json().get('qrn')
            # Break the long hex string into 8-character chunks (4 bytes each)
            chunks = [raw_hex[i:i+8] for i in range(0, len(raw_hex), 8)]
            for c in chunks:
                val = int(c, 16)
                QUANTUM_BUFFER.append((val % len(TOKENS), "QUANTUM (BUFFERED)"))
            return True
    except Exception as e:
        print(f"Buffer Refill Error: {e}")
    return False

@app.get("/invoke")
def invoke():
    # If buffer is empty, try to refill
    if not QUANTUM_BUFFER:
        success = refill_buffer()
        if not success:
            # Fallback to local if API is totally blocked
            return {"token": secrets.choice(TOKENS), "source": "LOCAL (FALLBACK)"}

    # Pop the next quantum outcome from our local queue
    idx, source = QUANTUM_BUFFER.popleft()
    return {"token": TOKENS[idx], "source": source}

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)