from __future__ import annotations
# IDEAFix local metrics (reimplemented from the paper's prose; the official repo ships no code for them). No judge.
#
# Per response (one output = one idea list L):
#   fluency    |L|
#   diversity  mean over ideas of min cosine distance (1 - cos) to the other ideas            [EMB_MODEL]
#   overlap    mean over ideas of |B & I_j| / |B|; B, I_j = lowercased lemmas of NOUN/PROPN/ADJ/ADV   [SPACY_MODEL]
#   perplexity median over ideas of GPT-2 exp(mean NLL), each idea scored after a BOS token    [LM_MODEL]
# Per brief: mean over valid samples. Aggregate: mean over briefs (perplexity also as median over briefs),
# for all briefs, non-classic and classic briefs separately. Headline = diversity over all briefs.
#
# Idea splitting (paper rules, our concrete choices):
#   - strip <think>, markdown bold/italics/headings/backticks; "Solution N:" and tabs start new lines;
#   - item line = starts with a bullet (-*•+), "N." / "N)" / "(N)" or "Solution N:"; a non-item line right after an
#     item (no blank line) continues that item; a non-item line of > 5 words after a blank line is prose and closes
#     the current list; text before the first item is dropped; with several lists only the last one is kept;
#   - ideas of <= 5 words are dropped; a response with <= 1 remaining idea is invalid (refusal / bad format).
#
# Record fields used: brief = inputs.user_request (else meta.brief); classic task flag = meta.classic_task.
# Extra dependencies: sentence-transformers, transformers, torch, spacy + the en_core_web_sm model
# (optional group `scoring-ideafix`).
import math
import re
import statistics as st
from pathlib import Path
from typing import Any
from mybench.schema import Record
from mybench.scoring.common import load_outputs, mean, pick, strip_think, summary

EMB_MODEL = "sentence-transformers/all-mpnet-base-v2"
LM_MODEL = "openai-community/gpt2"
SPACY_MODEL = "en_core_web_sm"
KEEP_POS = {"NOUN", "PROPN", "ADJ", "ADV"}
METRICS = ("fluency", "diversity", "overlap", "perplexity")
ITEM_RE = re.compile(r"^\s*(?:[-*•+]\s+|\(?\d+[.)]\s*|solution\s+\d+\s*[:.)-]\s*)", re.IGNORECASE)

def n_words(s: str) -> int:
    return len(s.split())

def split_ideas(text: str | None) -> list[str]:
    text = strip_think(text)
    text = re.sub(r"(?i)(?<!^)(?=\bsolution\s+\d+\s*:)", "\n", text)
    text = text.replace("\t", "\n")
    lines = [re.sub(r"\*\*|__|`", "", ln).strip() for ln in text.split("\n")]
    lines = [re.sub(r"^#+\s*", "", ln) for ln in lines]
    lists: list[list[str]] = []
    cur: list[str] = []
    last = "blank"  # kind of the previous line: blank | item | other
    for ln in lines:
        if not ln:
            last = "blank"
            continue
        m = ITEM_RE.match(ln)
        if m:
            cur.append(ln[m.end():].strip())  # bare marker ("1.") -> content arrives as continuation
            last = "item"
        elif cur and last == "item":
            cur[-1] = (cur[-1] + " " + ln).strip()  # continuation of the item
        else:
            if cur and last == "blank" and n_words(ln) > 5:
                lists.append(cur)  # prose paragraph closes the list
                cur = []
            last = "other"
    if cur:
        lists.append(cur)
    lists = [lst for lst in lists if lst]
    if not lists:
        return []
    ideas = [re.sub(r"\s+", " ", re.sub(r"(?<!\w)[*_](?!\w)|[*_]{2,}", "", i)).strip() for i in lists[-1]]
    ideas = [i for i in ideas if n_words(i) > 5]
    return ideas if len(ideas) > 1 else []

def score(records: list[Record], outputs_path: Path, *, model: str, device: str = "cpu") -> dict[str, Any]:
    import numpy as np
    import spacy
    import torch
    from sentence_transformers import SentenceTransformer
    from transformers import AutoModelForCausalLM, AutoTokenizer

    torch.set_grad_enabled(False)
    items = {r.id: r for r in records}
    raw = load_outputs(outputs_path, set(items))
    responses, errors, invalid = [], [], []
    for (iid, s), r in sorted(raw.items()):
        if "error" in r:
            errors.append({"id": iid, "sample": s, "error": r["error"]})
            continue
        ideas = split_ideas(r.get("output"))
        if not ideas:
            invalid.append({"id": iid, "sample": s, "head": strip_think(r.get("output"))[:200]})
            continue
        responses.append({"id": iid, "sample": s, "ideas": ideas})
    all_ideas = [i for r in responses for i in r["ideas"]]
    print(f"{model}/ideafix: {len(responses)} valid responses, {len(invalid)} invalid, {len(errors)} errors, "
          f"{len(all_ideas)} ideas", flush=True)

    emb = SentenceTransformer(EMB_MODEL, device=device).encode(all_ideas, batch_size=64, normalize_embeddings=True)
    nlp = spacy.load(SPACY_MODEL)

    def keywords(doc: Any) -> set[str]:
        return {t.lemma_.lower() for t in doc if t.pos_ in KEEP_POS}

    idea_kw = [keywords(d) for d in nlp.pipe(all_ideas, batch_size=256)]
    brief_kw = {iid: keywords(nlp(pick(rec, "inputs.user_request", "meta.brief", default=""))) for iid, rec in items.items()}

    tok = AutoTokenizer.from_pretrained(LM_MODEL)
    lm = AutoModelForCausalLM.from_pretrained(LM_MODEL).to(device).eval()
    ppl: list[float] = []
    for b in range(0, len(all_ideas), 32):
        enc = [[tok.bos_token_id] + tok.encode(t)[:1023] for t in all_ideas[b:b + 32]]
        L = max(map(len, enc))
        ids = torch.tensor([e + [tok.eos_token_id] * (L - len(e)) for e in enc], device=device)
        mask = torch.tensor([[1] * len(e) + [0] * (L - len(e)) for e in enc], device=device)
        logp = torch.log_softmax(lm(input_ids=ids, attention_mask=mask).logits[:, :-1].float(), -1)
        tgt = logp.gather(-1, ids[:, 1:, None])[..., 0] * mask[:, 1:]
        ppl += [math.exp(-(tgt[k].sum() / mask[k, 1:].sum()).item()) for k in range(len(enc))]

    pos = 0
    for r in responses:
        n = len(r["ideas"])
        E = emb[pos:pos + n]
        sim = E @ E.T
        np.fill_diagonal(sim, -np.inf)
        B = brief_kw[r["id"]]
        r["fluency"] = n
        r["diversity"] = float(np.mean(1.0 - sim.max(axis=1)))
        r["overlap"] = float(np.mean([len(B & k) / len(B) for k in idea_kw[pos:pos + n]])) if B else None
        r["perplexity"] = float(st.median(ppl[pos:pos + n]))
        pos += n

    per_item = []
    for iid, rec in items.items():
        rs = [r for r in responses if r["id"] == iid]
        n_err = sum(e["id"] == iid for e in errors)
        n_inv = sum(e["id"] == iid for e in invalid)
        if not rs and not n_err and not n_inv:
            continue  # not run
        x = {"id": iid, "classic_task": bool(pick(rec, "meta.classic_task", default=False)), "n_valid": len(rs),
             "n_invalid": n_inv, "n_errors": n_err}
        x.update({m: mean(r[m] for r in rs) for m in METRICS})
        per_item.append(x)

    def agg(xs: list[dict[str, Any]]) -> dict[str, Any]:
        ok = [x for x in xs if x["n_valid"]]
        out: dict[str, Any] = {"n_briefs": len(ok), **{m: mean(x[m] for x in ok) for m in METRICS}}
        out["perplexity_median_over_briefs"] = st.median([x["perplexity"] for x in ok]) if ok else None
        return out

    overall = agg(per_item)
    return summary(
        "ideafix", model,
        headline=overall["diversity"],
        metric="IDEAFix diversity (mean min cosine distance), all briefs",
        higher_is_better=True, scale="raw", stat="mean",
        items={x["id"]: {"score": x["diversity"], **{m: x[m] for m in METRICS if m != "diversity"}}
               for x in per_item if x["n_valid"]},
        n_expected=len(items), n_errors=len(errors) + len(invalid), n_covered=len(per_item),
        extra={"models": {"embedding": EMB_MODEL, "lm": LM_MODEL, "spacy": SPACY_MODEL,
                          "spacy_version": spacy.__version__},
               "n_ideas": len(all_ideas), "all": overall,
               "non_classic": agg([x for x in per_item if not x["classic_task"]]),
               "classic": agg([x for x in per_item if x["classic_task"]]), "errors": errors, "invalid": invalid},
    )
