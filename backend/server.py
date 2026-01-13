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

# --- NLTK DATA SETUP ---
nltk_data_path = os.path.join(os.getcwd(), "nltk_data")
if not os.path.exists(nltk_data_path):
    os.makedirs(nltk_data_path)
nltk.data.path.append(nltk_data_path)

for res in ['brown', 'stopwords']:
    try:
        nltk.data.find(f'corpora/{res}')
    except LookupError:
        nltk.download(res, download_dir=nltk_data_path, quiet=True)

brown_words = brown.tagged_words()
stop_words = set(stopwords.words('english'))

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

# --- ENTROPY LOGIC WITH TRACKING ---
def get_divine_index(limit):
    """Returns (index, source_name)"""
    try:
        r = requests.get("https://random.colorado.edu/api/get_bits", timeout=0.3)
        if r.status_code == 200:
            val = int(r.json()['bits'], 16) % limit
            return val, "PHYSICAL (CU COLORADO)"
    except:
        pass
    return secrets.randbelow(limit), "PSEUDO (SECRETS)"

def divine_choice(items):
    idx, _ = get_divine_index(len(items))
    return items[idx] if items else "void"

# --- GENERATION ---
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

@app.get("/")
def get_divination():
    # We generate the thought and also grab the source of the final roll
    thought = [generate_clause()]
    roll, source = get_divine_index(100)
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