import os
import json
import secrets
import requests
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# Enable CORS for Vercel
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load the 100k token library
# Ensure tokens.json is in your /backend folder
TOKEN_PATH = os.path.join(os.getcwd(), "tokens.json")
try:
    with open(TOKEN_PATH, "r") as f:
        TOKENS = json.load(f)
except Exception as e:
    print(f"Error loading tokens: {e}")
    TOKENS = ["[void]", "[null]", "[error]"]

def get_quantum_index(limit):
    """Fetch 4 bytes from LFDR QRNG and map to token library."""
    try:
        # Requesting 4 bytes in HEX to cover the 100k+ token range
        r = requests.get("https://lfdr.de/qrng_api/qrng?length=4&format=HEX", timeout=1.5)
        if r.status_code == 200:
            hex_val = r.json().get('qrn')
            int_val = int(hex_val, 16)
            return int_val % limit, "QUANTUM (LFDR.DE)"
    except:
        pass
    # Fallback to local entropy if API is down
    return secrets.randbelow(limit), "PSEUDO (LOCAL)"

@app.get("/invoke")
def invoke():
    idx, source = get_quantum_index(len(TOKENS))
    return {
        "token": TOKENS[idx],
        "source": source
    }

@app.get("/heartbeat")
def heartbeat():
    return {"status": "alive"}

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)