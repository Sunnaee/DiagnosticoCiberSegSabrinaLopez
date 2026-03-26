import os
import re
import time
import json
import ast
import requests
from datetime import datetime

VIS_URL = os.getenv("VISUALIZER_URL", "http://visualizer:4000/events")
HEADERS = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2026-03-10"}
SEARCH_URL = "https://api.github.com/search/repositories?q=stars:>1&sort=stars&order=desc&per_page=10"

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

def process_repo(item):
    owner = item["owner"]["login"]
    name = item["name"]
    branch = item.get("default_branch", "master")
    # list tree
    tree_url = f"https://api.github.com/repos/{owner}/{name}/git/trees/{branch}?recursive=1"
    r = requests.get(tree_url, headers=HEADERS)
    if r.status_code != 200:
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
            continue
        content = rr.text
        if path.endswith(".py"):
            words = extract_from_python(content)
        else:
            words = extract_from_java(content)
        for w in words:
            post_word(w, f"{owner}/{name}", path)
        print(f"Extracted {len(words)}")

def main_loop():
    while True:
        r = requests.get(SEARCH_URL, headers=HEADERS)
        if r.status_code != 200:
            time.sleep(10)
            continue
        items = r.json().get("items", [])
        for it in items:
            process_repo(it)
            time.sleep(30)
        time.sleep(15)

if __name__ == "__main__":
    main_loop()