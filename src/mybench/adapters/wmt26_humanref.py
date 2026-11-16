"""WMT26 EN->{cs,de,et}, paragraph level, human references only.

Why not the `wmt26` adapter: that one emits whole documents and skips every record with a
screenshot, which removes 41 of the 44 social (Mastodon) documents. The fresh selection uses single
paragraphs (`<p>...</p>` lines; source and human reference are 1:1 line-aligned in the news and
social domains) and keeps social documents as text only, so its items have no counterpart there.
Same raw file as `wmt26` (github.com/wmt-conference/wmt26-general-mt @ 63aa5d24311a7e7e3e8173528f3771c7e8b4be78).
"""
from __future__ import annotations
from collections.abc import Iterator
from pathlib import Path
from mybench.adapters.common import Skips, file_version, make_id, meta, read_jsonl
from mybench.adapters.wmt26 import LICENSE, RAW_FILE, short_lang
from mybench.schema import Record
from mybench.templates import render

SOURCE = "wmt26_humanref"
TEMPLATE = "wmt26-original"
TARGETS = ("ces_Latn", "deu_Latn", "ekk_Latn")  # refPE (human post-edit): ces, deu; refA (from scratch): ekk
DOMAINS = ("news", "social")  # speech needs the video, software is JSON UI strings
METRICX_MODEL = "google/metricx-24-hybrid-xl-v2p6-bfloat16"

def lines(text: str) -> list[str]:
    return [x for x in text.split("\n") if x.strip()]

def doc_name(doc_id: str) -> str:
    # WMT26_###_<domain>_###_eng_Latn_###_<tgt>_###_<doc> -> <doc>
    return doc_id.split("_###_")[-1]

def load(raw_dir: Path, skips: Skips) -> Iterator[Record]:
    path = raw_dir / RAW_FILE
    version = file_version(path)
    for row in read_jsonl(path):
        if row["src_lang"] != "eng_Latn" or row["tgt_lang"] not in TARGETS or row["domain"] not in DOMAINS:
            continue
        refs = row.get("refs") or {}
        if len(refs) != 1:
            skips.add("wmt26_humanref: not exactly one human reference")
            continue
        (ref_kind, ref_text), = refs.items()
        src_pars, ref_pars = lines(row["src_text"]), lines(ref_text)
        if len(src_pars) != len(ref_pars):
            skips.add("wmt26_humanref: source and reference paragraphs not aligned")
            continue
        src, tgt = short_lang(row["src_lang"]), short_lang(row["tgt_lang"])
        doc = doc_name(row["doc_id"])
        for i, (source_text, reference) in enumerate(zip(src_pars, ref_pars)):
            messages = render(TEMPLATE, prompt_instruction=row["prompt_instruction"], source_text=source_text)
            yield Record(
                id=make_id(SOURCE, f"{src}_{tgt}", row["domain"], doc, f"p{i}"),
                category="translation",
                subcategory=row["domain"],
                source=SOURCE,
                source_subset=f"{row['src_lang']}-{row['tgt_lang']}",
                source_id=f"{row['doc_id']}#{i}",
                source_version=version,
                source_license=LICENSE,
                lang=src,
                src_lang=src,
                tgt_lang=tgt,
                prompt_template_id=TEMPLATE,
                inputs={"source_text": source_text},
                messages=messages,
                reference={"translation": reference, "translation_kind": ref_kind},
                eval={
                    "type": "metric",
                    "params": {
                        "metrics": ["metricx24"],
                        "metricx_model": METRICX_MODEL,
                        "lower_is_better": True,
                        "temperature": 0.0,
                        "max_tokens": 2048,
                    },
                },
                meta=meta(
                    messages,
                    doc_id=row["doc_id"],
                    paragraph_index=i,
                    unit=f"{row['domain']}/{doc}#{i}",
                    has_screenshot=bool(row.get("screenshot")),
                ),
            )
