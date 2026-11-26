"""LPSession (2026-11-26): tir_dispute.Session that also records log-probabilities (vLLM logprobs=K on every completion), so results can be read by
token confidence and not by accuracy alone. Stored per session (small): number of generated tokens, mean sampled log-prob, DeepConf's token confidence
(2508.15260: C_i = −mean of the top-K log-probs at position i) as its mean and its lowest 1,024-token sliding-window mean ("lowest group confidence"),
the tail mean over the last 2,048 tokens, and the sampled log-probs of the final message's tokens (at most 64).
tir_dispute.py itself is unchanged (it is in use by running rows); new runs import this class."""
import os
from tir_dispute import Session
import tir_native as T
K = int(os.environ.get("LP_K", 5)); W = 1024


class LPSession(Session):
    def __init__(self, *a, **k):
        super().__init__(*a, **k); self.lp = []; self.conf = []; self.final_lp = []

    def gen(self, budget):
        import llm
        start = self.used
        while True:
            room = min(budget - (self.used - start), int(os.environ.get("TIR_CTX", 64000)) - len(self.ids) - 8)
            if room < 16:
                self.fin = "length"; return ""
            r = llm.client.completions.create(model="local", prompt=self.ids, temperature=1.0, top_p=0.95, max_tokens=room, seed=self.seed + self.calls + 7919 * self.turn, logprobs=K,
                                              extra_body={"return_token_ids": True, "skip_special_tokens": False, "stop_token_ids": [T.CALL, T.RET]})
            self.prefill += len(self.ids); c = r.choices[0]; g = list(c.token_ids); self.used += r.usage.completion_tokens; self.text = c.text or ""; self.fin = c.finish_reason
            L = c.logprobs; seg = [x for x in (L.token_logprobs or []) if x is not None] if L else []
            self.lp += seg
            if L and L.top_logprobs:
                self.conf += [-sum(d.values()) / len(d) for d in L.top_logprobs if d]
            if self.fin == "length":
                return ""
            if T.CALL in (g[-1] if g else None, c.stop_reason):
                if g[-1] != T.CALL:
                    g.append(T.CALL)
                m = self.text.split("<|call|>")[0].split("<|message|>"); head, code = m[-2].split("<|start|>")[-1] if len(m) > 1 else "", m[-1]
                self.calls += 1
                if self.calls > T.MAXCALLS:
                    self.fin = "calls"; return ""
                o = self.tool.run(code) if "python" in head else "Unknown tool. Only python is available."
                self.codes.append(code); self.outs.append(o)
                oi = self.tok(o); self.tooltok += len(oi); self.ids = self.ids + g + self.tok("<|start|>python to=assistant<|channel|>analysis<|message|>") + oi + self.tok("<|end|><|start|>assistant")
                continue
            self.g = g
            # the final message's tokens: after the last '<|channel|>final<|message|>' in this segment
            toks = (L.tokens or []) if L else []; j = max((i for i in range(len(toks) - 1) if toks[i] == "<|channel|>" and toks[i + 1].startswith("final")), default=None)
            self.final_lp = [x for x in (L.token_logprobs[j + 2:] if j is not None else []) if x is not None][:64]
            return self.text.split("<|channel|>final<|message|>")[-1].split("<|return|>")[0] if "<|channel|>final<|message|>" in self.text else ""

    def summary(self):
        c = self.conf; n = len(c)
        low = min((sum(c[i:i + W]) / W for i in range(0, max(1, n - W + 1), 128)), default=None) if n >= W else (sum(c) / n if n else None)
        return {"n": len(self.lp), "mean_lp": sum(self.lp) / len(self.lp) if self.lp else None, "mean_conf": sum(c) / n if n else None, "lowest_group_conf": low,
                "tail_conf": sum(c[-2048:]) / len(c[-2048:]) if n else None, "final_lp": [round(x, 3) for x in self.final_lp]}
