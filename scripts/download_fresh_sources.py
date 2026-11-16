"""Download the raw files of the fresh sources into data/raw/<source>/.

Every file is fetched from its official location at a pinned revision (HF dataset revision or
git commit) and checked against a pinned sha256. No authentication is used. The raw data is
licensed and gitignored; only this script is committed.

  python scripts/download_fresh_sources.py                      # all sources
  python scripts/download_fresh_sources.py --sources listqa     # selected sources
  python scripts/download_fresh_sources.py --force              # re-download existing files
"""
from __future__ import annotations
import argparse
import hashlib
import sys
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

LISTQA_REV = "748eb345a110c4a7cb2af6b6be8074840974e15f"  # HF AmazonScience/ListQA
VAGUEBENCH_REV = "62d4cc6f17cb5efaa46da02e7d42bbf64c96aa02"  # HF rongyu0101/VagueBench
SLOPBENCH_COMMIT = "4eb24d9b400ecbd31bf16b630cc0a8f3ffb3278f"  # github.com/hgaddipati1118/slop-index
# IDEAFix code + briefs: anonymous mirror without git history, so the pin is the sha256 below.
IDEAFIX_REPO = "CreativityAndEthicalFramework-C01E"
IDEAFIX_DIR = "data/202510_ProtocolCreativityEthics_VF"

def _hf(repo: str, rev: str, path: str) -> str:
    return f"https://huggingface.co/datasets/{repo}/resolve/{rev}/{path}"

def _gh(repo: str, commit: str, path: str) -> str:
    return f"https://raw.githubusercontent.com/{repo}/{commit}/{path}"

def _anon(path: str) -> str:
    return f"https://anonymous.4open.science/api/repo/{IDEAFIX_REPO}/file/{urllib.parse.quote(path)}"

# source -> [(local file name, url, sha256)]
FILES: dict[str, list[tuple[str, str, str]]] = {
    "listqa": [
        ("all.jsonl", _hf("AmazonScience/ListQA", LISTQA_REV, "data/all.jsonl"),
         "ecbc816e1f15b0fce6bd28cff9e3fd4a0db4b4599a3c31925a77235045029b90"),
    ],
    "vaguebench": [
        ("VagueBench_en.jsonl", _hf("rongyu0101/VagueBench", VAGUEBENCH_REV, "VagueBench_en.jsonl"),
         "77d025b671d83a0cd0730c9d590d4efe18d5539eaef90aabd7d6fb806b334265"),
    ],
    "slopbench": [
        (f"{domain}.json", _gh("hgaddipati1118/slop-index", SLOPBENCH_COMMIT, f"scenarios/pilot/{domain}.json"), sha)
        for domain, sha in (
            ("email", "08ac606f94366ab2263b3ffc704349292487497271a4d234084c54c4e3e17464"),
            ("social", "7176c92871dbfd607a214654026e580de99e59f4f454c75d3d2dcb37c45d827b"),
            ("essay", "1e39f32e74c46a0c26fafd66c4a2603be3526452f2e0430a5f22bd9f2b34facf"),
            ("slack", "94572d41726426f57acdbad5d1a1fbfa0c0f45533e81690477c7589fce327f7d"),
        )
    ],
    "ideafix": [
        ("Briefs-Table 1.csv", _anon(f"{IDEAFIX_DIR}/Briefs-Table 1.csv"),
         "e5b19495983348e93d89e972d192f8d96aa21b4e9177aaa7d935720b8aa77bd9"),
        ("Crea_prompts-Table 1.csv", _anon(f"{IDEAFIX_DIR}/Crea_prompts-Table 1.csv"),
         "71cf95770a397bc2888492e09c66b3fbf0e8c1ada1805f70e8562f6aa0879379"),
    ],
}

def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def fetch(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "mybench-downloader"})
    with urllib.request.urlopen(req, timeout=120) as resp:
        return resp.read()

def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--raw-dir", type=Path, default=ROOT / "data" / "raw")
    p.add_argument("--sources", nargs="+", choices=sorted(FILES), default=list(FILES))
    p.add_argument("--force", action="store_true", help="re-download files that already exist")
    args = p.parse_args()

    errors = 0
    for source in args.sources:
        out_dir = args.raw_dir / source
        out_dir.mkdir(parents=True, exist_ok=True)
        for name, url, expected in FILES[source]:
            out = out_dir / name
            if out.exists() and not args.force:
                data = out.read_bytes()
                action = "exists"
            else:
                data = fetch(url)
                action = "downloaded"
            digest = sha256(data)
            if digest != expected:
                print(f"[ERROR] {source}/{name}: sha256 {digest}, expected {expected}", file=sys.stderr)
                errors += 1
                continue
            if action == "downloaded":
                out.write_bytes(data)
            print(f"{source}/{name}: {action}, {len(data)} bytes, sha256 ok")
    if errors:
        print(f"\n{errors} files failed verification (not written).", file=sys.stderr)
        return 1
    return 0

if __name__ == "__main__":
    sys.exit(main())
