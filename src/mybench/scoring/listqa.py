from __future__ import annotations
# ListQA scoring: the official pipeline (ListQA-Eval) with the judge served behind an OpenAI-compatible endpoint.
#
# Parsing, ROUGE/Hungarian pairing, format correctness, relaxed EM, ROUGE list metrics and the LLM-Judge-F1
# aggregation are imported from a local clone of https://github.com/amazon-science/ListQA-Eval (`<listqa_dir>/src`),
# not copied. Only the judge call is ours: about `batch_pairs` (question, gold element, predicted element) pairs per
# call, whole items only, JSON response validated; an invalid batch is retried once, then graded with official
# single-element calls (3 tries, else B). Judge grades are cached (resumable) in `cache_path`.
#
# Record fields used: question = inputs.user_request (else the text after "Question:" in the last user message);
# gold answer string = reference.answer (else reference.baseline_answer); ListQA metadata JSON = meta.metadata
# (else built from meta.prompt_type / meta.category / meta.country / meta.year_range).
# Extra dependencies: evaluate, rouge-score, scipy, nltk, absl-py (optional group `scoring-listqa`).
import functools
import hashlib
import json
import re
import sys
import threading
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any
from mybench.run.runner import chat
from mybench.schema import Record
from mybench.scoring.common import last_user_message, load_outputs, mean, pick, read_jsonl, strip_think, summary

BATCH_PAIRS = 20
# Explicit schema so the server enforces the {"grades": [{"k", "grade"}]} shape.
GRADES_SCHEMA = {
    "type": "object",
    "required": ["grades"],
    "additionalProperties": False,
    "properties": {
        "grades": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["k", "grade"],
                "additionalProperties": False,
                "properties": {"k": {"type": "integer"}, "grade": {"enum": ["A", "B"]}},
            },
        }
    },
}

def question(rec: Record) -> str:
    q = pick(rec, "inputs.user_request")
    if q:
        return q
    return last_user_message(rec).rsplit("Question:", 1)[-1].strip()

def metadata_json(rec: Record) -> str:
    md = pick(rec, "meta.metadata")
    if md is None:
        md = {k: pick(rec, f"meta.{k}") for k in ("prompt_type", "category", "country", "year_range")}
        md = {k: v for k, v in md.items() if v is not None}
    return md if isinstance(md, str) else json.dumps(md, ensure_ascii=False)

class Judge:
    def __init__(self, base_url: str, model: str, api_key: str | None, system: str, single_prompt: Callable[..., str]):
        self.base_url, self.model, self.api_key = base_url, model, api_key
        self.system, self.single_prompt = system, single_prompt

    def ask(self, messages: list[dict[str, str]], json_mode: bool) -> str:
        payload: dict[str, Any] = {"model": self.model, "messages": messages, "temperature": 0}
        if json_mode:
            payload["response_format"] = {
                "type": "json_schema",
                "json_schema": {"name": "grades", "schema": GRADES_SCHEMA},
            }
        return chat(self.base_url, payload, self.api_key)["choices"][0]["message"]["content"] or ""

    def single(self, q: str, t: str, p: str, max_retries: int = 3) -> str:
        """Official per-element judging. Unparsable after retries -> B; no response at all -> raise (not cached)."""
        answered = False
        for _ in range(max_retries):
            try:
                resp = self.ask([{"role": "user", "content": self.single_prompt(q, t, p)}], json_mode=False)
                answered = True
            except Exception as e:  # noqa: BLE001
                print("  judge error:", repr(e)[:200], flush=True)
                continue
            m = re.search(r"^\s*(A|B)\s*$", resp, re.MULTILINE)
            if m:
                return m.group(1)
        if not answered:
            raise RuntimeError("judge unreachable")
        return "B"

    def batch(self, pairs: list[tuple[str, str, str]]) -> tuple[list[str], str]:
        msgs = [{"role": "system", "content": self.system}, {"role": "user", "content": batch_prompt(pairs)}]
        for _ in range(2):  # first try + one retry
            try:
                grades = parse_batch(self.ask(msgs, json_mode=True), len(pairs))
                if grades:
                    return grades, "batch"
            except Exception as e:  # noqa: BLE001
                print("  batch judge error:", repr(e)[:200], flush=True)
        return [self.single(*x) for x in pairs], "single"

def batch_prompt(pairs: list[tuple[str, str, str]]) -> str:
    blocks = [
        f"### Example {k}\n```\nQuestion: {q}\nGold target: {t}\nPredicted answer: {p}\n```"
        for k, (q, t, p) in enumerate(pairs, 1)
    ]
    return (
        f"Here are {len(pairs)} new examples. Grade each one independently, exactly as you would grade a single example.\n\n"
        + "\n\n".join(blocks)
        + '\n\nReturn JSON only: {"grades": [{"k": 1, "grade": "A"}, …]} with A = CORRECT, B = INCORRECT, '
        "one entry per example, in order."
    )

def parse_batch(text: str, n: int) -> list[str] | None:
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if not m:
        return None
    try:
        out = [str(g["grade"]).strip().upper() for g in json.loads(m.group(0))["grades"]]
    except (ValueError, KeyError, TypeError):
        return None
    return out if len(out) == n and all(g in ("A", "B") for g in out) else None

def score(
    records: list[Record],
    outputs_path: Path,
    *,
    model: str,
    listqa_dir: Path,
    cache_path: Path,
    judge_url: str,
    judge_model: str,
    judge_api_key: str | None = None,
    concurrency: int = 4,
    batch_pairs: int = BATCH_PAIRS,
) -> dict[str, Any]:
    sys.path.insert(0, str(listqa_dir / "src"))
    import evaluate
    from listqa_eval import metrics as M
    from listqa_eval.aggregator import aggregate_llm_judge_scores
    from listqa_eval.prompts import LLM_JUDGE_PROMPT_TEMPLATE, format_judge_prompt

    M.load_metric = functools.lru_cache(maxsize=None)(evaluate.load)  # same metric, loaded once
    system = LLM_JUDGE_PROMPT_TEMPLATE.split("\n\nHere is a new example.")[0]  # shared instructions + examples
    judge = Judge(judge_url, judge_model, judge_api_key, system, format_judge_prompt)

    items = {r.id: r for r in records}
    rows = load_outputs(outputs_path, set(items))
    cache = {c["key"]: c for c in read_jsonl(cache_path)}

    # 1. parse + pair (official code)
    work: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    for (iid, s), r in sorted(rows.items()):
        if "error" in r:
            errors.append({"id": iid, "sample": s, "error": r["error"]})
            continue
        rec = items[iid]
        pred = strip_think(r.get("output"))
        answer = pick(rec, "reference.answer", "reference.baseline_answer")
        pairs, n_pred, n_gold = M.get_rouge_best_match_ranked_lists(answer, pred, 0.0, "rouge1")
        key = f"{iid}|{s}|{hashlib.sha1(pred.encode()).hexdigest()[:16]}"
        work.append(dict(id=iid, sample=s, rec=rec, pred=pred, answer=answer, pairs=pairs, n_pred=n_pred,
                         n_gold=n_gold, key=key))

    # 2. judge (batched by whole items, cached)
    todo = [w for w in work if w["key"] not in cache]
    batches: list[list[dict[str, Any]]] = []
    cur: list[dict[str, Any]] = []
    cur_n = 0
    for w in todo:
        n = sum(p["target"] is not None and bool(p["pred"].strip()) for p in w["pairs"])
        if cur and cur_n + n > batch_pairs:
            batches.append(cur)
            cur, cur_n = [], 0
        cur.append(w)
        cur_n += n
    if cur:
        batches.append(cur)
    print(f"{model}/listqa: {len(work)} outputs, {len(errors)} errors, {len(work) - len(todo)} cached, "
          f"{len(batches)} judge batches", flush=True)

    lock = threading.Lock()
    cache_path.parent.mkdir(parents=True, exist_ok=True)

    def run_batch(ws: list[dict[str, Any]]) -> str:
        flat, slots = [], []
        for wi, w in enumerate(ws):
            q = question(w["rec"])
            for pi, p in enumerate(w["pairs"]):
                if p["target"] is not None and p["pred"].strip():
                    flat.append((q, p["target"], p["pred"]))
                    slots.append((wi, pi))
        grades, method = judge.batch(flat) if flat else ([], "auto")
        per = [["B"] * len(w["pairs"]) for w in ws]  # target=None / empty pred -> automatic B
        for (wi, pi), g in zip(slots, grades):
            per[wi][pi] = g
        recs = [{"key": w["key"], "id": w["id"], "sample": w["sample"], "grades": per[wi], "method": method,
                 "judge": judge_model} for wi, w in enumerate(ws)]
        with lock, cache_path.open("a", encoding="utf-8", newline="\n") as f:
            for rec in recs:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
                cache[rec["key"]] = rec
        return method

    with ThreadPoolExecutor(max(1, concurrency)) as ex:
        futs = [ex.submit(run_batch, b) for b in batches]
        for i, fut in enumerate(as_completed(futs), 1):
            try:
                m = fut.result()
            except Exception as e:  # noqa: BLE001
                m = f"FAILED {e!r}"[:200]
            if i % 10 == 0 or i == len(futs) or m != "batch":
                print(f"  batch {i}/{len(futs)} ({m})", flush=True)

    unjudged = [w for w in work if w["key"] not in cache]
    if unjudged:
        raise RuntimeError(f"{len(unjudged)} outputs still unjudged (judge failures); re-run to resume")

    # 3. per-item scores + official aggregation
    results, per_item = [], []
    for w in work:
        grades = cache[w["key"]]["grades"]
        md = metadata_json(w["rec"])
        n_a = sum(g == "A" for g in grades)
        p = n_a / w["n_pred"] if w["n_pred"] else 0.0
        r = n_a / w["n_gold"] if w["n_gold"] else 0.0
        prompt_type = json.loads(md).get("prompt_type")
        per_item.append({
            "id": w["id"], "sample": w["sample"], "prompt_type": prompt_type, "precision": p, "recall": r,
            "f1": 2 * p * r / (p + r) if p + r else 0.0, "format_correct": M.compute_list_format_em(w["pred"], md),
            "relaxed_em_precision": M.compute_relaxed_precision_list_em(w["answer"], w["pred"]),
            "relaxed_em_recall": M.compute_relaxed_recall_list_em(w["answer"], w["pred"]),
            "rouge_list_f1": M.compute_rouge_list_match(w["answer"], w["pred"])["rouge_list_f1"],
            "judge_method": cache[w["key"]]["method"],
        })
        results.append({"metadata": md, "prompt_type": prompt_type, "llm_judge": {
            "list_element_scores": [{"score": g} for g in grades],
            "num_pred_list_elements": w["n_pred"], "num_target_list_elements": w["n_gold"]}})

    agg = aggregate_llm_judge_scores(results)
    zero = {"llm_judge": {"list_element_scores": [], "num_pred_list_elements": 0, "num_target_list_elements": 0}}
    items_out = {x["id"]: {"score": x["f1"], "p": x["precision"], "r": x["recall"]} for x in per_item if x["sample"] == 0}
    return summary(
        "listqa", model,
        headline=agg["f1"],
        metric="LLM-Judge-F1 (official aggregator: 2PR/(P+R) of item-mean P and R)",
        higher_is_better=True, scale="0-1", stat="f1_pr", items=items_out, n_expected=len(items),
        n_errors=len(errors), n_covered=len(items_out) + len({e["id"] for e in errors} - set(items_out)),
        extra={
            "judge": judge_model, "batch_pairs": batch_pairs,
            "llm_judge_precision": agg["precision"], "llm_judge_recall": agg["recall"],
            "llm_judge_f1_errors_as_zero": aggregate_llm_judge_scores(results + [zero] * len(errors))["f1"],
            "simple": aggregate_llm_judge_scores([x for x in results if x["prompt_type"] == "single-faceted"]),
            "complex": aggregate_llm_judge_scores([x for x in results if x["prompt_type"] == "multi-faceted"]),
            "by_category": agg.get("category"),
            **{k: mean(x[k] for x in per_item) for k in ("format_correct", "relaxed_em_precision",
                                                          "relaxed_em_recall", "rouge_list_f1")},
            "judge_methods": {m: sum(x["judge_method"] == m for x in per_item) for m in ("batch", "single", "auto")},
            "errors": errors,
        },
    )
