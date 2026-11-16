from __future__ import annotations
import string
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

# Verbatim LISTQA_ZERO_SHOT_PROMPT from github.com/amazon-science/ListQA-Eval
# (src/listqa_eval/prompts.py @ 83faa7c3a089a7c835c89f408f44b5b88ed27469).
LISTQA_ZERO_SHOT_PROMPT = (
    "Answer the question below by producing a list-formatted output, "
    "lists can be formatted one of two ways:\n\n"
    "For simple questions with few constraints requesting only main elements "
    "and not requesting sub-elements, use the following format:\n"
    "1. List Element 1\n"
    "2. List Element 2\n\n"
    "For complex questions asking for multiple factoids in addition to the "
    "primary question, use the following format:\n"
    "1. List Element 1\n"
    "* Category 1: Sub-Element 1\n"
    "* Category 2: Sub-Element 2\n\n"
    "2. List Element2\n"
    "* Category 1: Sub-Element 1\n"
    "* Category 2: Sub-Element 2\n\n"
    "All answers are bounded by 3 to 10 main elements, do not generate more "
    "than 10 main elements in the list. Do not add any information that is "
    "not asked for in the question.\n"
    "Question: {question}"
)

@register("listqa-zero-shot")
def listqa_zero_shot(*, user_request: str) -> Messages:
    """ListQA official zero-shot prompt (one user turn, no system message)."""
    return [{"role": "user", "content": LISTQA_ZERO_SHOT_PROMPT.format(question=user_request)}]

@register("ideafix-control")
def ideafix_control(*, control_prompt: str, user_request: str) -> Messages:
    """IDEAFix "Prompt - Control condition / Alternative 1" with `[Brief context]` replaced by
    the brief name, as in the official `Prompt.create_prompt_with_brief` (one user turn)."""
    return [{"role": "user", "content": control_prompt.replace("[Brief context]", user_request)}]