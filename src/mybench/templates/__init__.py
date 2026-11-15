import string
from __future__ import annotations
from collections.abc import Callable
from typing import Any

Messages = list[dict[str, str]]
TemplateFn = Callable[..., Messages]

TEMPLATES: dict[str, TemplateFn] = {}

def register(template_id: str) -> Callable[[TemplateFn], TemplateFn]:
    def deco(fn: TemplateFn) -> TemplateFn:
        if template_id in TEMPLATES:
            raise ValueError(f"template {template_id!r} is already registered")
        TEMPLATES[template_id] = fn
        return fn

    return deco

def render(template_id: str, **fields: Any) -> Messages:
    try:
        fn = TEMPLATES[template_id]
    except KeyError:
        raise KeyError(f"unknown prompt_template_id: {template_id!r}") from None
    return fn(**fields)

def choice_letters(n: int) -> list[str]:
    if n > len(string.ascii_uppercase):
        raise ValueError(f"too many options ({n}) for letters A-Z")
    return list(string.ascii_uppercase[:n])

@register("chat-raw")
def chat_raw(*, user_request: str, system_instruction: str | None = None) -> Messages:
    """The user prompt, unchanged."""
    msgs: Messages = []
    if system_instruction:
        msgs.append({"role": "system", "content": system_instruction})
    msgs.append({"role": "user", "content": user_request})
    return msgs

@register("mc-v1")
def mc_v1(*, question: str, choices: list[str]) -> Messages:
    """Multiple choice, zero-shot, no forced CoT; the answer is a letter."""
    letters = choice_letters(len(choices))
    options = "\n".join(f"{l}) {c}" for l, c in zip(letters, choices))
    content = (
        "Answer the following multiple choice question.\n\n"
        f"Question: {question}\n\n"
        f"Options:\n{options}\n\n"
        f"The last line of your response must be exactly \"Answer: X\", "
        f"where X is one of the letters {letters[0]}-{letters[-1]}."
    )
    return [{"role": "user", "content": content}]

@register("wmt26-original")
def wmt26_original(*, prompt_instruction: str, source_text: str) -> Messages:
    """Original WMT26 instruction (ends with 'Please translate the following text into ...:')."""
    return [{"role": "user", "content": f"{prompt_instruction.rstrip()}\n\n{source_text}"}]

@register("facts-original")
def facts_original(*, full_prompt: str) -> Messages:
    """FACTS Grounding: the original `full_prompt` as a single user turn.

    In the raw data `full_prompt` is not a simple concatenation of the columns
    (different formatting, appended URLs), so it is not rebuilt from `inputs`.
    """
    return [{"role": "user", "content": full_prompt}]

@register("facts-split")
def facts_split(
    *, system_instruction: str, context_document: str, user_request: str
) -> Messages:
    """Variant: instruction as the system role, document and request in the user turn."""
    return [
        {"role": "system", "content": system_instruction},
        {"role": "user", "content": f"{context_document}\n\n{user_request}"},
    ]