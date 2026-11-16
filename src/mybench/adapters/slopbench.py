from __future__ import annotations
import json
from collections.abc import Iterator
from pathlib import Path
from mybench.adapters.common import Skips, file_version, make_id, meta
from mybench.schema import Record
from mybench.templates import render

SOURCE = "slopbench"
LICENSE = "MIT (code); prompts CC-BY-4.0"
# github.com/hgaddipati1118/slop-index @ 4eb24d9b400ecbd31bf16b630cc0a8f3ffb3278f, scenarios/pilot/
DOMAINS = ("email", "social", "essay", "slack")  # same order as harness/generate.py
TEMPLATE = "chat-raw"
SCORER = "github.com/hgaddipati1118/slop-index@4eb24d9b400ecbd31bf16b630cc0a8f3ffb3278f harness/score.py"
N_SAMPLES = 5  # the templating axis needs >= 2 samples of the same scenario

# Verbatim from harness/generate.py
SCAFFOLD = {
    "email": "You are helping the user write an email. Output only the email body, no subject line, no commentary.",
    "social": "You are helping the user write a social media post. Output only the post text, no commentary.",
    "essay": "You are helping the user write. Output only the piece itself, no commentary.",
    "slack": "You are helping the user write a Slack message. Output only the message, as they would send it, no commentary.",
}

def build_user_prompt(s: dict) -> str:
    """Verbatim from harness/generate.py."""
    parts = [f"About me: {s['persona']}"]
    if s.get("recipient"):
        parts.append(f"Who this is going to: {s['recipient']}")
    for m in s.get("context_thread", []):
        who = {"recipient": "They wrote", "persona": "I previously wrote",
               "other": "Context"}.get(m["from"], "Context")
        parts.append(f'{who}: "{m["text"]}"')
    parts.append(f"\n{s['prompt']}")
    return "\n".join(parts)

def load(raw_dir: Path, skips: Skips) -> Iterator[Record]:
    for domain in DOMAINS:
        path = raw_dir / SOURCE / f"{domain}.json"
        version = file_version(path)
        for s in json.loads(path.read_text(encoding="utf-8")):
            user_request = build_user_prompt(s)
            messages = render(TEMPLATE, user_request=user_request, system_instruction=SCAFFOLD[domain])
            yield Record(
                id=make_id(SOURCE, s["id"]),
                category="writing",
                subcategory=domain,
                source=SOURCE,
                source_subset=s["category"],
                source_id=s["id"],
                source_version=version,
                source_license=LICENSE,
                lang="en",
                prompt_template_id=TEMPLATE,
                inputs={"user_request": user_request, "system_instruction": SCAFFOLD[domain]},
                messages=messages,
                reference={"length_target_words": s["length_target"]["words"]},
                eval={
                    "type": "metric",
                    "params": {
                        "metric": "slop_index",
                        "scorer": SCORER,
                        "axes": ["conciseness", "templating", "rhythm", "tells"],
                        "n_samples": N_SAMPLES,
                        "max_tokens": 4000,  # official; retry once with 8000 if the visible text is empty
                        "strip_thinking": True,
                    },
                    "group_size": N_SAMPLES,
                },
                # goal/author_note are for analysis only; they are not sent to the model.
                meta=meta(messages, goal=s.get("goal"), author_note=s.get("author_note")),
            )
