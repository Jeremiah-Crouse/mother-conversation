import nltk
from nltk.corpus import brown, stopwords
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import secrets
import requests
import os
import uvicorn

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- NLTK DATA SETUP (LOCAL ONLY) ---
# We no longer download; we simply point to the bundled directory
nltk_data_path = os.path.join(os.getcwd(), "nltk_data")
nltk.data.path.append(nltk_data_path)

# Pre-load the data into memory for instant generation
try:
    brown_words = brown.tagged_words()
    stop_words = set(stopwords.words('english'))
except Exception as e:
    print(f"Error loading bundled NLTK data: {e}")
    # Fallback to empty if data is missing to prevent crash
    brown_words = []
    stop_words = set()

def get_lex_weighted(tags, start_with_vowel=None):
    vowels = 'aeiou'
    filtered = []
    for w, t in brown_words:
        w_low = w.lower()
        if t not in tags or not w.isalpha() or len(w) < 4 or w_low in stop_words:
            continue
        if start_with_vowel is True and w_low[0] not in vowels:
            continue
        if start_with_vowel is False and w_low[0] in vowels:
            continue
        filtered.append(w_low)
    return list(set(filtered))

# Build the Lexicon once during startup
LEXICON = {
    "N_sg_v": get_lex_weighted(['NN', 'NNP'], start_with_vowel=True),
    "N_sg_c": get_lex_weighted(['NN', 'NNP'], start_with_vowel=False),
    "N_pl": get_lex_weighted(['NNS', 'NNPS']),
    "Adj_v": get_lex_weighted(['JJ'], start_with_vowel=True),
    "Adj_c": get_lex_weighted(['JJ'], start_with_vowel=False),
    "V_sg": get_lex_weighted(['VBZ']), 
    "V_pl": get_lex_weighted(['VBP', 'VB']),
    "Adv": ['ceaselessly', 'eternally', 'blindly', 'utterly', 'solemnly', 'precisely', 'silently', 'purely']
}

# --- MULTI-TIER ENTROPY LOGIC ---

def get_divine_index(limit):
    if limit <= 1: return 0, "DETERMINISTIC"

    # 1. Quantum (CUB)
    try:
        r = requests.get("https://random.colorado.edu/api/get_bits?type=quantum", timeout=0.3)
        if r.status_code == 200:
            return int(r.json()['bits'], 16) % limit, "QUANTUM (CUB)"
    except:
        pass

    # 2. Physical (CUB)
    try:
        r = requests.get("https://random.colorado.edu/api/get_bits?type=classical", timeout=0.3)
        if r.status_code == 200:
            return int(r.json()['bits'], 16) % limit, "PHYSICAL (CUB CLASSICAL)"
    except:
        pass

    # 3. Atmospheric (Random.org)
    try:
        r = requests.get(f"https://www.random.org/integers/?num=1&min=0&max={limit-1}&col=1&base=10&format=plain&rnd=new", timeout=0.4)
        if r.status_code == 200:
            return int(r.text.strip()), "ATMOSPHERIC (RANDOM.ORG)"
    except:
        pass

    # 4. Fallback
    return secrets.randbelow(limit), "PSEUDO (LOCAL SECRETS)"

def divine_choice(items):
    idx, _ = get_divine_index(len(items))
    return items[idx] if items else "void"

# --- GENERATION ENGINE ---

def generate_clause():
    s = []
    leads = ['a', 'an', 'the', 'thy', 'thou']
    idx, _ = get_divine_index(5)
    lead = leads[idx]
    s.append(lead)
    
    if lead == 'an':
        s.extend([divine_choice(LEXICON["Adj_v"]), divine_choice(LEXICON["N_sg_v"]), divine_choice(LEXICON["V_sg"])])
    elif lead == 'a':
        s.extend([divine_choice(LEXICON["Adj_c"]), divine_choice(LEXICON["N_sg_c"]), divine_choice(LEXICON["V_sg"])])
    elif lead in ['the', 'thy']:
        chance, _ = get_divine_index(2)
        if chance == 0:
            s.extend([divine_choice(LEXICON["N_pl"]), divine_choice(LEXICON["V_pl"])])
        else:
            s.extend([divine_choice(LEXICON["N_sg_c"] + LEXICON["N_sg_v"]), divine_choice(LEXICON["V_sg"])])
    elif lead == 'thou':
        s.extend([divine_choice(LEXICON["V_pl"])])

    s.append(divine_choice(LEXICON["Adv"]))
    return " ".join(s)

# --- ENDPOINTS ---

@app.get("/")
def get_divination():
    roll, source = get_divine_index(100)
    thought = [generate_clause()]
    if roll < 30:
        conjunctions = ['because', 'yet', 'as', 'while', 'for', 'though']
        thought.extend([divine_choice(conjunctions), generate_clause()])
    
    return {
        "message": " ".join(thought),
        "source": source
    }

@app.get("/heartbeat")
def heartbeat():
    return {"status": "alive"}

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)