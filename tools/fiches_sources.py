#!/usr/bin/env python3
"""Rapatrie la doc de chaque firmware du catalogue, au commit du catalogue, pour la rédaction des fiches.

Usage : python3 -I tools/fiches_sources.py [dest]      (dest : .fiches-sources par défaut)
Crée <dest>/<id>/repo : un clone partiel dont seuls les fichiers de doc sont extraits au `commit_source`.
Affiche une ligne par firmware : id, nombre de fichiers de doc, octets. Le code des dépôts n'est jamais exécuté.
"""
import json
import os
import re
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEST = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, ".fiches-sources"))

DOC = re.compile(r"(^|/)(readme|manual|guide|usage)[^/]*\.(md|txt|pdf)$|^docs?/|(^|/)(web|site)/[^/]*help[^/]*$", re.I)
SKIP = re.compile(r"node_modules|vendor|third_party|(^|/)sdk/|emsdk|\.(png|jpe?g|gif|svg|webp|wasm|bin|fwsc)$", re.I)


def git(*a, cwd=None):
    return subprocess.run(["git", *a], cwd=cwd, capture_output=True, text=True, timeout=600)


def fetch(e):
    m = re.match(r"https://github\.com/([^/]+)/([^/#?]+)", e["depot"])
    repo = os.path.join(DEST, e["id"], "repo")
    if not m:
        return e["id"], 0, 0, "dépôt hors GitHub"
    if not os.path.isdir(os.path.join(repo, ".git")):
        os.makedirs(repo, exist_ok=True)
        r = git("clone", "-q", "--filter=blob:none", "--no-checkout", f"https://github.com/{m[1]}/{m[2].removesuffix('.git')}", repo)
        if r.returncode:
            return e["id"], 0, 0, "clone : " + r.stderr.strip()[:80]
    ls = git("ls-tree", "-r", "--name-only", e["commit_source"], cwd=repo)
    if ls.returncode:
        return e["id"], 0, 0, "commit introuvable"
    files = [f for f in ls.stdout.splitlines() if DOC.search(f) and not SKIP.search(f)]
    if files:
        r = git("checkout", e["commit_source"], "--", *files, cwd=repo)
        if r.returncode:
            return e["id"], 0, 0, "extraction : " + r.stderr.strip()[:80]
    size = sum(os.path.getsize(os.path.join(repo, f)) for f in files if os.path.exists(os.path.join(repo, f)))
    return e["id"], len(files), size, ""


def main():
    cat = json.load(open(os.path.join(ROOT, "firmwares/catalogue.json"), encoding="utf-8"))["firmwares"]
    with ThreadPoolExecutor(6) as ex:
        for id_, n, size, err in ex.map(fetch, cat):
            print(f"{id_:14} {n:4} {size:9}  {err}".rstrip())


if __name__ == "__main__":
    main()
