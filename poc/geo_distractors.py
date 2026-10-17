"""Distractor helper pools for the geometry toolbox dose-response (S4d).
RELATED: tested, correct geometry helpers; per task we drop the ones the task NEEDS (always given separately) and the ones that
would SOLVE the task outright. UNRELATED: tested non-geometry helpers (a semantic-distance control of equal kind)."""
import random

RELATED = {
    "orient": "def orient(a, b, c):            # >0 left turn, <0 right turn, 0 collinear (exact for integers)\n    return (b[0]-a[0])*(c[1]-a[1]) - (b[1]-a[1])*(c[0]-a[0])\n",
    "on_segment": "def on_segment(a, b, p):        # p lies on the closed segment ab\n    return orient(a, b, p) == 0 and min(a[0],b[0]) <= p[0] <= max(a[0],b[0]) and min(a[1],b[1]) <= p[1] <= max(a[1],b[1])\n",
    "segments_intersect": "def segments_intersect(a, b, c, d):   # closed segments ab and cd share at least one point\n    d1, d2, d3, d4 = orient(c,d,a), orient(c,d,b), orient(a,b,c), orient(a,b,d)\n    if ((d1>0 and d2<0) or (d1<0 and d2>0)) and ((d3>0 and d4<0) or (d3<0 and d4>0)): return True\n    return on_segment(c,d,a) or on_segment(c,d,b) or on_segment(a,b,c) or on_segment(a,b,d)\n",
    "point_in_polygon": "def point_in_polygon(poly, q):  # 'inside' / 'outside' / 'boundary' (winding number, exact)\n    wn = 0\n    for i in range(len(poly)):\n        a, b = poly[i], poly[(i+1) % len(poly)]\n        if on_segment(a, b, q): return 'boundary'\n        if a[1] <= q[1]:\n            if b[1] > q[1] and orient(a, b, q) > 0: wn += 1\n        elif b[1] <= q[1] and orient(a, b, q) < 0: wn -= 1\n    return 'inside' if wn != 0 else 'outside'\n",
    "dist2": "def dist2(a, b):                # squared Euclidean distance (exact)\n    return (a[0]-b[0])**2 + (a[1]-b[1])**2\n",
    "bbox": "def bbox(points):               # (min_x, min_y, max_x, max_y)\n    xs = [p[0] for p in points]; ys = [p[1] for p in points]\n    return min(xs), min(ys), max(xs), max(ys)\n",
    "collinear": "def collinear(a, b, c):          # True if the three points lie on one line\n    return orient(a, b, c) == 0\n",
    "polar_sort": "def polar_sort(points, o):      # points sorted counter-clockwise by angle around o (exact, no atan2)\n    import functools\n    def half(p): return 0 if (p[1]-o[1] > 0 or (p[1] == o[1] and p[0]-o[0] > 0)) else 1\n    def cmp(p, q):\n        if half(p) != half(q): return half(p) - half(q)\n        c = orient(o, p, q)\n        return -1 if c > 0 else (1 if c < 0 else dist2(o, p) - dist2(o, q))\n    return sorted(points, key=functools.cmp_to_key(cmp))\n",
    "is_convex": "def is_convex(poly):            # True if the polygon (in order) is convex\n    n = len(poly); s = 0\n    for i in range(n):\n        c = orient(poly[i], poly[(i+1) % n], poly[(i+2) % n])\n        if c != 0:\n            if s == 0: s = 1 if c > 0 else -1\n            elif (c > 0) != (s > 0): return False\n    return True\n",
    "polygon_area2": "def polygon_area2(poly):        # twice the signed area (shoelace, exact)\n    return sum(poly[i][0]*poly[(i+1) % len(poly)][1] - poly[(i+1) % len(poly)][0]*poly[i][1] for i in range(len(poly)))\n",
    "convex_hull": "def convex_hull(points):        # hull vertices in CCW order, collinear points dropped (monotone chain)\n    P = sorted(set(points))\n    if len(P) <= 2: return P\n    lo, up = [], []\n    for p in P:\n        while len(lo) >= 2 and orient(lo[-2], lo[-1], p) <= 0: lo.pop()\n        lo.append(p)\n    for p in reversed(P):\n        while len(up) >= 2 and orient(up[-2], up[-1], p) <= 0: up.pop()\n        up.append(p)\n    return lo[:-1] + up[:-1]\n",
    "closest_pair_sq": "def closest_pair_sq(points):     # smallest squared distance between two of the points (O(n^2))\n    return min(dist2(points[i], points[j]) for i in range(len(points)) for j in range(i+1, len(points)))\n",
}
NEW = {   # E2 (pre-registered 2026-10-13): helpers for the new tasks; kept OUT of RELATED so the K-distractor draws of all older tasks are unchanged
    "in_circle": "def in_circle(a, b, c, d):      # exact in-circle test for a counter-clockwise triangle abc: > 0 inside, 0 on, < 0 outside its circumcircle\n    ax, ay, bx, by, cx, cy = a[0]-d[0], a[1]-d[1], b[0]-d[0], b[1]-d[1], c[0]-d[0], c[1]-d[1]\n    return (ax*ax + ay*ay) * (bx*cy - cx*by) - (bx*bx + by*by) * (ax*cy - cx*ay) + (cx*cx + cy*cy) * (ax*by - bx*ay)\n",
    "circumcenter": "def circumcenter(a, b, c):      # centre (x, y) of the circle through a, b, c (floating point)\n    d = 2 * (a[0]*(b[1]-c[1]) + b[0]*(c[1]-a[1]) + c[0]*(a[1]-b[1]))\n    ux = ((a[0]**2 + a[1]**2)*(b[1]-c[1]) + (b[0]**2 + b[1]**2)*(c[1]-a[1]) + (c[0]**2 + c[1]**2)*(a[1]-b[1])) / d\n    uy = ((a[0]**2 + a[1]**2)*(c[0]-b[0]) + (b[0]**2 + b[1]**2)*(a[0]-c[0]) + (c[0]**2 + c[1]**2)*(b[0]-a[0])) / d\n    return ux, uy\n",
}
INCIRCLE_VARIANTS = {   # E2 F2-replication: the needed helper with its orientation contract terse (as given), spelled out, or removed
    "signed": NEW["in_circle"],
    "doc": NEW["in_circle"].replace("# exact in-circle test for a counter-clockwise triangle abc: > 0 inside, 0 on, < 0 outside its circumcircle",
                                    "# exact in-circle test: > 0 inside, 0 on, < 0 outside the circumcircle of abc. WARNING: valid only if a, b, c are "
                                    "in COUNTER-CLOCKWISE order; for a clockwise triangle the sign is reversed"),
    "fixed": NEW["in_circle"].replace("# exact in-circle test for a counter-clockwise triangle abc: > 0 inside, 0 on, < 0 outside its circumcircle",
                                      "# exact in-circle test, any vertex order: > 0 inside, 0 on, < 0 outside the circumcircle of triangle abc")
                             .replace("    return (ax*ax", "    o = (b[0]-a[0])*(c[1]-a[1]) - (b[1]-a[1])*(c[0]-a[0])\n    return (1 if o > 0 else -1) * ((ax*ax")
                             .replace("(ax*by - bx*ay)\n", "(ax*by - bx*ay))\n"),
}
DEPS = {"on_segment": ["orient"], "segments_intersect": ["orient", "on_segment"], "point_in_polygon": ["orient", "on_segment"],
        "collinear": ["orient"], "polar_sort": ["orient", "dist2"], "is_convex": ["orient"], "convex_hull": ["orient"],
        "closest_pair_sq": ["dist2"]}
NEED = {"hull": ["orient"], "pip": ["orient", "on_segment", "point_in_polygon"],
        "segs": ["orient", "on_segment", "segments_intersect"], "area2": [], "close": [], "convex": ["orient"], "tri": ["orient"],
        "overlap": ["orient", "on_segment", "segments_intersect", "point_in_polygon"], "lattice": ["polygon_area2"], "rectunion": [], "clip": ["orient"],
        "delaunay": ["in_circle"], "diameter": [], "hullL": ["orient"], "closeL": [], "diamL": []}
SOLVES = {"hull": ["convex_hull"], "area2": ["polygon_area2"], "close": ["closest_pair_sq"],
          "pip": ["point_in_polygon"], "segs": ["segments_intersect"], "convex": ["is_convex"], "tri": ["point_in_polygon"], "overlap": [], "lattice": [], "rectunion": [], "clip": [],
          "delaunay": [], "diameter": [], "hullL": ["convex_hull"], "closeL": ["closest_pair_sq"], "diamL": []}
UNRELATED = {
    "gcd": "def gcd(a, b):                  # greatest common divisor\n    while b: a, b = b, a % b\n    return abs(a)\n",
    "is_prime": "def is_prime(n):                # primality by trial division\n    if n < 2: return False\n    i = 2\n    while i * i <= n:\n        if n % i == 0: return False\n        i += 1\n    return True\n",
    "fib": "def fib(n):                     # n-th Fibonacci number (fib(0) = 0)\n    a, b = 0, 1\n    for _ in range(n): a, b = b, a + b\n    return a\n",
    "reverse_words": "def reverse_words(s):           # 'a b c' -> 'c b a'\n    return ' '.join(reversed(s.split()))\n",
    "lower_bound": "def lower_bound(arr, x):        # first index i with arr[i] >= x in a sorted list\n    lo, hi = 0, len(arr)\n    while lo < hi:\n        m = (lo + hi) // 2\n        if arr[m] < x: lo = m + 1\n        else: hi = m\n    return lo\n",
    "lcs_len": "def lcs_len(a, b):              # length of the longest common subsequence of two strings\n    dp = [0] * (len(b) + 1)\n    for ca in a:\n        prev = 0\n        for j, cb in enumerate(b):\n            cur = dp[j + 1]\n            dp[j + 1] = prev + 1 if ca == cb else max(dp[j + 1], dp[j])\n            prev = cur\n    return dp[-1]\n",
}
HEAD = "You may (and should) use these tested helper functions; copy the ones you use into your program unchanged:\n```python\n"
HEAD_PRELUDE = ("These tested helper functions are ALREADY DEFINED in the environment that runs your program: call any of them directly, "
                "do not copy or redefine them.\n```python\n")
HEAD_NEUTRAL = "The following tested helper functions are available:\n```python\n"   # review item 2: no instruction at all
HEAD_MAY = ("Some tested helper functions are listed below. Most of them are probably NOT needed for this task: use one only if it directly "
            "helps, and copy any helper you use into your program unchanged.\n```python\n")


def with_deps(names):
    full, stack = [], list(names)
    while stack:
        n = stack.pop(0)
        if n not in full:
            full.append(n); stack += DEPS.get(n, [])
    return full


def render_names(names, head="should"):
    src = {**RELATED, **UNRELATED, **NEW}
    return ((HEAD if head == "should" else HEAD_MAY) + "".join(src[n] for n in names) + "```") if names else ""


def catalog(names):
    """one line per helper: signature + its comment (what the model sees in auto-scope stage 1)"""
    src = {**RELATED, **UNRELATED, **NEW}   # NEW: in_circle (delaunay); N10 crashed on it 2026-10-16
    out = []
    for n in names:
        first = src[n].splitlines()[0]
        sig, _, doc = first.partition("#")
        out.append(f"- {sig.replace('def ', '').rstrip(': ').strip()}: {doc.strip()}")
    return "\n".join(out)


def toolbox(task, k, kind, rng, head="should", fixed=None):
    """task-matched helpers + k distractors ('related' geometry or 'unrelated'), dependencies included, order shuffled.
    fixed: an explicit distractor list (E4 pre-registered similarity sets) instead of a random draw."""
    names = list(NEED[task])
    pool = ([n for n in RELATED if n not in NEED[task] and n not in SOLVES[task]] if kind == "related" else list(UNRELATED))
    names += list(fixed) if fixed is not None else rng.sample(pool, min(k, len(pool)))
    full, stack = [], list(names)
    while stack:   # add dependencies
        n = stack.pop(0)
        if n not in full:
            full.append(n); stack += DEPS.get(n, [])
    if not full:
        return "", []
    rng.shuffle(full)
    src = {**RELATED, **UNRELATED, **NEW}
    head_txt = {"should": HEAD, "may": HEAD_MAY, "prelude": HEAD_PRELUDE, "neutral": HEAD_NEUTRAL}[head]
    return head_txt + "".join(src[n] for n in full) + "```", [n for n in full if n not in NEED[task]]
