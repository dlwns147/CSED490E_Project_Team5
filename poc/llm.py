"""Thin OpenAI-compatible client (llama-server on CPU now, vLLM on GPU later — same code)."""
import os
import re
from concurrent.futures import ThreadPoolExecutor

from openai import OpenAI

BASE_URL = os.environ.get("POC_BASE_URL", "http://127.0.0.1:8080/v1")
client = OpenAI(base_url=BASE_URL, api_key="none", timeout=float(os.environ.get("POC_TIMEOUT", 3600)))   # long thinking: raise it
EFFORT = os.environ.get("POC_REASONING_EFFORT")   # gpt-oss: low / medium / high (passed as reasoning_effort; other models ignore it)
_EFF = {"reasoning_effort": EFFORT} if EFFORT else {}
QEFF = os.environ.get("POC_TEMPLATE_EFFORT")   # Qwen3.6/3.8 templates: reasoning_effort in chat_template_kwargs (xhigh default | medium | low)
_TK = {"reasoning_effort": QEFF} if QEFF else {}
# sampling for thinking calls from the model card, e.g. POC_THINK_SAMPLING=temperature=1.0,top_p=0.95,top_k=20,presence_penalty=1.5
# (Qwen3.6; 2026-10-17: our default T 0.7 / no presence penalty left 13% of its competition-math thinking runs unfinished at 28k)
_TS = {k: float(v) for k, v in (kv.split("=") for kv in os.environ["POC_THINK_SAMPLING"].split(","))} if os.environ.get("POC_THINK_SAMPLING") else {}
SEED = os.environ.get("POC_SEED")   # HO-SEED: Seed-OSS template, thinking set by thinking_budget (0 = off, -1 = unlimited, B = its own budget)


def chat(prompt: str, model: str = "local", temperature: float = 0.7, max_tokens: int = 1024,
         system: str | None = None, think: bool = False, seed: int | None = None, prefill: str | None = None,
         logprobs: bool = False, top_logprobs: int = 0, effort: str | None = None, budget: int | None = None) -> dict:
    """effort: gpt-oss reasoning_effort for this call only (default: POC_REASONING_EFFORT); budget: Seed-OSS native thinking budget"""
    msgs = ([{"role": "system", "content": system}] if system else []) + [{"role": "user", "content": prompt}]
    if prefill:  # assistant prefill (llama-server continues the message; vLLM: continue_final_message)
        msgs.append({"role": "assistant", "content": prefill})
    ts = _TS if think else {}
    r = client.chat.completions.create(
        model=model, messages=msgs, temperature=ts.get("temperature", temperature), top_p=ts.get("top_p", 0.95 if temperature > 0 else 1.0),
        max_tokens=max_tokens, seed=seed, **({"logprobs": True} if logprobs or top_logprobs else {}),
        **({"top_logprobs": top_logprobs} if top_logprobs else {}),
        **({"presence_penalty": ts["presence_penalty"]} if "presence_penalty" in ts else {}),
        extra_body={"chat_template_kwargs": {"enable_thinking": think, **_TK, **({"thinking_budget": (budget or -1) if think else 0} if SEED else {})},
                    **(_EFF if effort is None else {"reasoning_effort": effort}), **({"top_k": int(ts["top_k"])} if "top_k" in ts else {}),
                    # vLLM needs these to continue an assistant prefill; llama-server ignores them
                    **({"continue_final_message": True, "add_generation_prompt": False} if prefill else {})},
    )
    msg = r.choices[0].message
    text = (msg.content or "").replace("<seed:think>", "<think>").replace("</seed:think>", "</think>")   # Seed-OSS think tags
    if prefill and not text.startswith(prefill):
        text = prefill + text
    if think and "</think>" not in text and r.choices[0].finish_reason == "length":
        text = ""   # reasoning never closed: no final answer (2026-10-14: a code block inside truncated reasoning used to be taken)
    elif "</think>" in text:
        text = text.split("</think>")[-1]   # templates that open <think> in the prompt (Qwen3.5-arch models) emit only the closing tag
    out = {"text": strip_think(text), "finish": r.choices[0].finish_reason,
           "out_tokens": r.usage.completion_tokens, "in_tokens": r.usage.prompt_tokens}
    if logprobs:   # raw-model log-probs of the sampled tokens (vLLM default logprobs_mode=raw_logprobs), for confidence analysis
        lc = r.choices[0].logprobs.content or []
        out.update(lp=[t.logprob for t in lc], lp_tok=[t.token for t in lc])
    if top_logprobs:   # DeepConf-style token confidence: minus the mean log-prob of the top-k candidates at each position
        lc = r.choices[0].logprobs.content or []
        out.update(lp=[t.logprob for t in lc], lp_tok=[t.token for t in lc],
                   ctop=[-sum(x.logprob for x in t.top_logprobs) / max(1, len(t.top_logprobs)) for t in lc])
    return out


def n_tokens(text: str) -> int:
    """tokens of `text` under the served model's tokenizer (vLLM /tokenize; HO-SEED: a native think = out_tokens - answer tokens)"""
    return post_json("/tokenize", {"model": "local", "prompt": text, "add_special_tokens": False})["count"]


def post_json(path: str, body: dict) -> dict:
    """POST to the vLLM server's own endpoints (outside /v1); stdlib only (the client venv has no httpx / requests)"""
    import json, urllib.request
    req = urllib.request.Request(BASE_URL.rsplit("/v1", 1)[0] + path, data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read())


def strip_think(t: str) -> str:
    return re.sub(r"<think>.*?</think>", "", t, flags=re.S).strip()


def last_block(text: str, langs=("", "input", "text", "txt", "plaintext")) -> str | None:
    blocks = re.findall(r"```([a-zA-Z0-9_+-]*)[ \t]*\n(.*?)```", text, flags=re.S)
    blocks = [b for lang, b in blocks if lang.lower() in langs and b.strip()]   # skip empty blocks (gpt-oss doubles "```python")
    if blocks:
        return blocks[-1]
    # fallback (gpt-oss): an unbalanced extra fence (e.g. a trailing "```\n```") shifts the pairing above, so take the last
    # explicitly tagged opening fence and read up to the next fence
    for lang in [l for l in langs if l]:
        i = text.rfind(f"```{lang}\n")
        if i >= 0:
            body = text[i + len(lang) + 4:]
            j = body.find("```")
            return body[:j] if j >= 0 else body
    return None


def chat_many(prompts, workers: int = 8, **kw):
    with ThreadPoolExecutor(workers) as ex:
        return list(ex.map(lambda p: chat(p, **kw) if isinstance(p, str) else chat(p[0], **{**kw, **p[1]}), prompts))


def chat_msgs(msgs: list, model: str = "local", temperature: float = 0.7, max_tokens: int = 1024,
              think: bool = False, seed: int | None = None, client_=None, logprobs: bool = False) -> dict:
    """multi-turn variant: msgs = [{"role": ..., "content": ...}, ...]"""
    ts = _TS if think else {}
    r = (client_ or client).chat.completions.create(
        model=model, messages=msgs, temperature=ts.get("temperature", temperature), top_p=ts.get("top_p", 0.95 if temperature > 0 else 1.0),
        max_tokens=max_tokens, seed=seed, **({"logprobs": True} if logprobs else {}),
        **({"presence_penalty": ts["presence_penalty"]} if "presence_penalty" in ts else {}),
        extra_body={"chat_template_kwargs": {"enable_thinking": think, **_TK}, **_EFF, **({"top_k": int(ts["top_k"])} if "top_k" in ts else {})})
    text = r.choices[0].message.content or ""
    out = {"text": strip_think(text), "finish": r.choices[0].finish_reason,
           "out_tokens": r.usage.completion_tokens, "in_tokens": r.usage.prompt_tokens}
    if logprobs:   # N16: raw log-probs of the sampled answer tokens
        lc = r.choices[0].logprobs.content or []
        out.update(lp=[t.logprob for t in lc], lp_tok=[t.token for t in lc])
    return out
