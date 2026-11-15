from __future__ import annotations
from collections import defaultdict
from collections.abc import Iterator
from pathlib import Path
from mybench.adapters.common import Skips, file_version, make_id, meta, pad, read_jsonl
from mybench.schema import Record
from mybench.templates import render

SOURCE = "wmt26"
LICENSE = "none (no license required for academic use)"
RAW_FILE = Path("wmt26/wmt26-genmt.jsonl")
TEMPLATE = "wmt26-original"
REF_PRIORITY = ("refA", "refPE")  # refA: human translation; refPE: post-edited MT

# WMT codes (ISO 639-3 + script) -> short codes used in the lang/src_lang/tgt_lang fields.
LANG_CODES = {
    "eng_Latn": "en",
    "ces_Latn": "cs",
    "deu_Latn": "de",
    "ukr_Cyrl": "uk",
    "vie_Latn": "vi",
    "arz_Arab": "arz",
    "bel_Cyrl": "be",
    "ekk_Latn": "et",
    "hye_Armn": "hy",
    "ind_Latn": "id",
    "isl_Latn": "is",
    "jpn_Jpan": "ja",
    "kaz_Cyrl": "kk",
    "kor_Hang": "ko",
    "lij_Latn": "lij",
    "lld_Latn": "lld",
    "rus_Cyrl": "ru",
    "sme_Latn": "se",
    "tha_Thai": "th",
    "zho_Hans": "zh-Hans",
    "zho_Hant_TW": "zh-Hant-TW",
    "pol_Latn": "pl",
}

def short_lang(code: str) -> str:
    return LANG_CODES.get(code, code)

def pick_reference(refs: dict | None) -> tuple[str, str] | None:
    for kind in REF_PRIORITY:
        text = (refs or {}).get(kind)
        if text and text.strip():
            return kind, text
    return None

def load(raw_dir: Path, skips: Skips) -> Iterator[Record]:
    path = raw_dir / RAW_FILE
    version = file_version(path)
    counters: dict[str, int] = defaultdict(int)
    for row in read_jsonl(path):
        if row.get("video") or row.get("screenshot"):
            skips.add("wmt26: multimodal record (video/screenshot)")
            continue
        ref = pick_reference(row.get("refs"))
        if ref is None:
            skips.add("wmt26: no reference")
            continue
        if not row["src_text"].strip():
            skips.add("wmt26: empty source text")
            continue
        ref_kind, ref_text = ref
        src, tgt = short_lang(row["src_lang"]), short_lang(row["tgt_lang"])
        pair = f"{src}_{tgt}"
        messages = render(
            TEMPLATE, prompt_instruction=row["prompt_instruction"], source_text=row["src_text"]
        )
        yield Record(
            id=make_id(SOURCE, pair, pad(counters[pair])),
            category="translation",
            subcategory=row["domain"],
            source=SOURCE,
            source_subset=f"{row['src_lang']}-{row['tgt_lang']}",
            source_id=row["doc_id"],
            source_version=version,
            source_license=LICENSE,
            lang=src,
            src_lang=src,
            tgt_lang=tgt,
            prompt_template_id=TEMPLATE,
            inputs={"source_text": row["src_text"]},
            messages=messages,
            reference={"translation": ref_text, "translation_kind": ref_kind},
            eval={
                "type": "metric",
                "params": {
                    "metrics": ["comet", "chrf"],
                    # WMT guidance for the evaluator (e.g. for GEMBA-MQM).
                    "evaluation_instruction": row.get("evaluation_instruction"),
                },
            },
            meta=meta(messages),
        )
        counters[pair] += 1