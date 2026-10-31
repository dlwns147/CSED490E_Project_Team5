"""XG smoke diagnostic: what gpt-oss returns through the chat endpoint for a BFCL prompt-mode request (content, tool calls, the end of
its reasoning). usage: POC_BASE_URL=... python diag_oss_tc.py [k items]"""
import json, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from llm import client  # noqa: E402

P = [json.loads(l) for l in open(os.path.join(os.environ.get("POC_DATA", ""), "bfcl", "tc_items.jsonl"))][::200][:int(sys.argv[1]) if len(sys.argv) > 1 else 6]
for p in P:
    r = client.chat.completions.create(model="local", messages=[{"role": "system", "content": p["system"]}, {"role": "user", "content": p["user"]}],
                                       max_tokens=2048, temperature=0.7, seed=1, extra_body={"reasoning_effort": "low"})
    m = r.choices[0].message
    rc = getattr(m, "reasoning_content", None) or getattr(m, "reasoning", None) or ""
    print(json.dumps({"id": p["id"], "finish": r.choices[0].finish_reason, "content": (m.content or "")[:200],
                      "tool_calls": [(t.function.name, t.function.arguments[:120]) for t in (m.tool_calls or [])],
                      "reasoning_tail": rc[-200:], "tokens": r.usage.completion_tokens}), flush=True)
