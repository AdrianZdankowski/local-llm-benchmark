from __future__ import annotations
import csv
from collections.abc import Iterator
from pathlib import Path
from mybench.adapters.common import Skips, file_version, make_id, meta
from mybench.schema import Record
from mybench.templates import render

SOURCE = "ideafix"
LICENSE = "CC-BY-4.0 (data); code MIT"
# anonymous.4open.science/r/CreativityAndEthicalFramework-C01E, data/202510_ProtocolCreativityEthics_VF/
BRIEFS_FILE = Path("ideafix/Briefs-Table 1.csv")
PROMPTS_FILE = Path("ideafix/Crea_prompts-Table 1.csv")
TEMPLATE = "ideafix-control"
PROMPT_METHOD, PROMPT_VERSION = "Prompt - Control condition", "Alternative 1"
EXCLUDE = {"E": "jailbreak", "O": "ethical dilemma"}  # brief category letters left out of the benchmark
CLASSIC = {"L", "N"}  # classic creativity task / from the literature: likely contaminated
N_SAMPLES = 3  # the paper runs 3 independent generations per prompt

def read_rows(path: Path) -> list[list[str]]:
    # Default newline handling, as in the official code: CRLF inside cells becomes "\n".
    with path.open(encoding="utf-8", errors="replace") as f:
        return list(csv.reader(f))

def parse_briefs(rows: list[list[str]]) -> list[tuple[str, str]]:
    """(name, category letters) per brief; mirrors BriefFactory.from_csv (blocks of 5 rows)."""
    briefs = []
    for i in range(0, len(rows), 5):
        name, cats = rows[i][0].strip().split("|", 1)
        letters = set(cats.strip().strip("<").strip(">").strip())
        briefs.append((name.strip(), "".join(sorted(letters))))
    return briefs

def control_prompt(rows: list[list[str]]) -> str:
    header = rows[0]
    for r in rows[1:]:
        if r[0].strip() == PROMPT_METHOD:
            for h, cell in zip(header[1:], r[1:]):
                if h.strip() == PROMPT_VERSION:
                    return cell.strip()
    raise KeyError(f"{PROMPT_METHOD} / {PROMPT_VERSION}")

def load(raw_dir: Path, skips: Skips) -> Iterator[Record]:
    briefs_path, prompts_path = raw_dir / BRIEFS_FILE, raw_dir / PROMPTS_FILE
    version = f"{file_version(briefs_path)}+{file_version(prompts_path)}"
    template = control_prompt(read_rows(prompts_path))
    for idx, (name, cats) in enumerate(parse_briefs(read_rows(briefs_path))):
        excluded = [EXCLUDE[c] for c in cats if c in EXCLUDE]
        if excluded:
            skips.add(f"ideafix: brief category {' + '.join(excluded)}")
            continue
        # Neutral framing only: the brief name without an attribute adjective.
        messages = render(TEMPLATE, control_prompt=template, user_request=name)
        yield Record(
            id=make_id(SOURCE, f"brief-{idx:02d}"),
            category="chat",
            subcategory="classic" if set(cats) & CLASSIC else "applied",
            source=SOURCE,
            source_subset=f"{PROMPT_METHOD} | {PROMPT_VERSION}",
            source_id=name,
            source_version=version,
            source_license=LICENSE,
            lang="en",
            prompt_template_id=TEMPLATE,
            inputs={"user_request": name},
            messages=messages,
            eval={
                "type": "diversity",
                "params": {
                    # Paper metrics, reimplemented (no official code): per response, then mean over samples.
                    "metrics": ["fluency", "diversity", "overlap", "perplexity"],
                    "embedding_model": "sentence-transformers/all-mpnet-base-v2",
                    "spacy_model": "en_core_web_sm",
                    "perplexity_model": "openai-community/gpt2",
                    "n_samples": N_SAMPLES,
                    "max_tokens": 8192,
                    "strip_thinking": True,
                },
                "group_size": N_SAMPLES,
            },
            meta=meta(
                messages,
                brief_index=idx,
                brief_categories=cats,
                classic_task=bool(set(cats) & CLASSIC),
                canonical_key=f"{PROMPT_METHOD}|{PROMPT_VERSION}|{name}||neutral",
            ),
        )
