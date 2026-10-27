"""HO-SEED smoke (docs/prereg/PREREG_HO.md; not part of the results): the hand-rendered Seed-OSS chat format of seed_budget_chat must
equal the server's template (unlimited thinking), and the budget-0 prompt must open the think block as the card says."""
import os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from llm import post_json  # noqa: E402

q = "A farmer has 3 fields of 12 hectares. How many hectares in total?"


def tok(**kw):
    return post_json("/tokenize", {"model": "local", **kw})["tokens"]


def text(t):
    return post_json("/detokenize", {"model": "local", "tokens": t})["prompt"]


msgs = [{"role": "user", "content": q}]
srv = tok(messages=msgs, add_generation_prompt=True, chat_template_kwargs={"thinking_budget": -1})
hand = tok(prompt=f"<seed:bos>user\n{q}<seed:eos><seed:bos>assistant\n", add_special_tokens=False)
print("unlimited: hand-rendered head == server template:", srv == hand, f"({len(srv)} / {len(hand)} tokens)")
if srv != hand:
    print("  server:", repr(text(srv)), "\n  hand:  ", repr(text(hand)))
for b in (0, 2048):
    print(f"thinking_budget {b}: prompt =", repr(text(tok(messages=msgs, add_generation_prompt=True, chat_template_kwargs={"thinking_budget": b}))))
