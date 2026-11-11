"""PREREG_NPC addendum NPC-L, offline: choose a trip-plan checker without labels. Dawid-Skene with several populations (Hui-Walter): latent wrong/right
per count-1 plan; per checker a catch rate k and false-flag rate f shared across translators; per translator a wrong share p; EM from 20 random starts.
Labels are used only to report the truth beside the estimates. usage: python3 poc/np_labelfree.py"""
import json, os, random, math
R = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "results")
TR, CH = ["q8b", "q32", "oss20", "oss120"], ["q8b", "q32", "oss120"]
def load(t, c):
    f = os.path.join(R, f"np_{t}_checkt{'' if c == t else '_' + c}.jsonl")
    return {(x["id"], x["tr"], x["seed"]): x for x in map(json.loads, open(f))}
items = []  # (translator, exact, [flag per checker])
for t in TR:
    F = {c: load(t, c) for c in CH}
    for k in sorted(set.intersection(*[set(F[c]) for c in CH])):
        items.append((t, F[CH[0]][k]["exact"], [int(bool(F[c][k]["violated"])) for c in CH]))
def em(seed, it=500):
    rng = random.Random(seed)
    k = {c: rng.uniform(.5, .99) for c in CH}; f = {c: rng.uniform(.01, .5) for c in CH}; p = {t: rng.uniform(.02, .4) for t in TR}
    for _ in range(it):
        post, ll = [], 0.0
        for t, _, fl in items:
            a, b = p[t], 1 - p[t]
            for c, x in zip(CH, fl):
                a *= k[c] if x else 1 - k[c]; b *= f[c] if x else 1 - f[c]
            post.append(a / (a + b)); ll += math.log(a + b)
        for t in TR:
            w = [q for (tt, _, _), q in zip(items, post) if tt == t]; p[t] = min(max(sum(w) / len(w), 1e-4), 1 - 1e-4)
        for j, c in enumerate(CH):
            sw = sum(post); k[c] = min(max(sum(q * fl[j] for (_, _, fl), q in zip(items, post)) / sw, 1e-4), 1 - 1e-4)
            f[c] = min(max(sum((1 - q) * fl[j] for (_, _, fl), q in zip(items, post)) / (len(items) - sw), 1e-4), 1 - 1e-4)
    return ll, k, f, p
fits = sorted((em(s) for s in range(20)), key=lambda z: -z[0])
fits = [z for z in fits if sum(z[2][c] < z[1][c] for c in CH) >= 2] or fits
ll, k, f, p = fits[0]
def wil(x, n):
    z = 1.96; m = (x + z * z / 2) / (n + z * z); h = z * math.sqrt(x * (n - x) / n + z * z / 4) / (n + z * z); return m - h, m + h
print(f"{len(items)} plans with all three checks; log-likelihood {ll:.1f}")
for j, c in enumerate(CH):
    W = [fl[j] for _, ex, fl in items if not ex]; G = [fl[j] for _, ex, fl in items if ex]
    print(f"checker {c:6s}: est catch {k[c]:.3f} false-flag {f[c]:.3f} | true catch {sum(W)}/{len(W)} = {sum(W) / len(W):.3f}, "
          f"false-flag {sum(G)}/{len(G)} = {sum(G) / len(G):.3f}; L1 {'holds' if abs(f[c] - sum(G) / len(G)) <= .05 else 'fails'}")
for t in TR:
    I = [ex for tt, ex, _ in items if tt == t]; w = sum(not e for e in I); lo, hi = wil(w, len(I))
    pick = max(CH, key=lambda c: p[t] * k[c] - (1 - p[t]) * f[c])
    print(f"translator {t:6s}: est wrong share {p[t]:.3f} | true {w}/{len(I)} = {w / len(I):.3f} [{lo:.3f}, {hi:.3f}]; label-free pick {pick}")
