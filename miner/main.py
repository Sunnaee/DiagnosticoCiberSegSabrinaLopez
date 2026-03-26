import os
import re
import time
import json
import ast
import requests
from datetime import datetime

VIS_URL = os.getenv("VISUALIZER_URL", "http://visualizer:4000/events")
HEADERS = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2026-03-10"}
SEARCH_URL = "https://api.github.com/search/repositories?q=stars:>1&sort=stars&order=desc&per_page=50"

# archivo para evitar reprocesar repos entre reinicios
PROCESSED_FILE = os.getenv("PROCESSED_FILE", "/app/processed.json")

def load_processed():
    try:
        with open(PROCESSED_FILE, "r", encoding="utf8") as f:
            return set(json.load(f))
    except Exception:
        return set()

def save_processed(s):
    try:
        os.makedirs(os.path.dirname(PROCESSED_FILE), exist_ok=True)
        with open(PROCESSED_FILE, "w", encoding="utf8") as f:
            json.dump(list(s), f)
    except Exception as e:
        print("save_processed error", e)

processed = load_processed()

def split_identifier(name):
    # snake_case
    parts = []
    for p in name.split("_"):
        # camelCase
        parts += re.findall(r'[A-Z]?[a-z]+|[A-Z]+(?![a-z])|\d+', p)
    return [s.lower() for s in parts if s]

def extract_from_python(src):
    words = []
    try:
        tree = ast.parse(src)
    except Exception:
        return words
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            words += split_identifier(node.name)
    return words

JAVA_METHOD_RE = re.compile(r'(?:public|protected|private)?\s*(?:static\s+)?[\w\<\>\[\]]+\s+([a-zA-Z_][\w]*)\s*\(', re.MULTILINE)

def extract_from_java(src):
    names = JAVA_METHOD_RE.findall(src)
    words = []
    for n in names:
        words += split_identifier(n)
    return words

def post_word(word, repo, path):
    payload = {"word": word, "repo": repo, "path": path, "ts": datetime.utcnow().isoformat()}
    try:
        requests.post(VIS_URL, json=payload, timeout=5)
    except Exception:
        pass

def _log_response(r, where):
    try:
        hdrs = []
        for h in ("X-RateLimit-Limit","X-RateLimit-Remaining","X-RateLimit-Reset","Retry-After"):
            if h in r.headers:
                hdrs.append(f"{h}={r.headers[h]}")
        print(f"{where} -> {r.status_code} {r.reason} {'; '.join(hdrs)}")
    except Exception:
        print(f"{where} -> {r.status_code if r is not None else 'no-response'}")

def _handle_rate_limit(r):
    # retorna segundos a esperar
    if not r:
        return 60
    if 'Retry-After' in r.headers:
        try:
            return int(r.headers['Retry-After'])
        except Exception:
            pass
    if 'X-RateLimit-Reset' in r.headers:
        try:
            reset = int(r.headers['X-RateLimit-Reset'])
            wait = max(0, reset - int(time.time())) + 5
            return wait
        except Exception:
            pass
    return 60

def process_repo(item):
    full = f"{item['owner']['login']}/{item['name']}"
    if full in processed:
        # ya procesado antes
        return
    owner = item["owner"]["login"]
    name = item["name"]
    branch = item.get("default_branch", "master")
    # list tree
    tree_url = f"https://api.github.com/repos/{owner}/{name}/git/trees/{branch}?recursive=1"
    r = requests.get(tree_url, headers=HEADERS)
    if r.status_code != 200:
        _log_response(r, f"tree {full}")
        if r.status_code in (403, 429):
            wait = _handle_rate_limit(r)
            print(f"Rate-limited, sleeping {wait}s")
            time.sleep(wait)
        return
    tree = r.json().get("tree", [])
    for file in tree:
        print(f"Processing {owner}/{name} - {file.get('path','')}")
        path = file.get("path","")
        if not path.endswith((".py", ".java")):
            continue
        raw_url = f"https://raw.githubusercontent.com/{owner}/{name}/{branch}/{path}"
        rr = requests.get(raw_url, headers=HEADERS)
        if rr.status_code != 200:
            _log_response(rr, f"raw {full}/{path}")
            # si raw falla por rate limit, espera un poco
            if rr.status_code in (403,429):
                wait = _handle_rate_limit(rr)
                print(f"Rate-limited on raw, sleeping {wait}s")
                time.sleep(wait)
            continue
        content = rr.text
        if path.endswith(".py"):
            words = extract_from_python(content)
        else:
            words = extract_from_java(content)
        for w in words:
            post_word(w, f"{owner}/{name}", path)
        print(f"Extracted {len(words)}")
    # marcar como procesado y persistir para evitar repetir tras reinicio
    processed.add(full)
    save_processed(processed)

def main_loop():
    # aumentar intervalo para evitar agotar limites
    while True:
        r = requests.get(SEARCH_URL, headers=HEADERS)
        if r.status_code != 200:
            _log_response(r, "search")
            if r.status_code in (403,429):
                wait = _handle_rate_limit(r)
                print(f"Search rate-limited, sleeping {wait}s")
                time.sleep(wait)
                continue
            time.sleep(30)
            continue
        items = r.json().get("items", [])
        for it in items:
            process_repo(it)
            time.sleep(2)
        time.sleep(60)  # repetir búsqueda con menor frecuencia

if __name__ == "__main__":
    main_loop()