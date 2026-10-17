"""Review item 7: automatic harness sanity check (CPU, no LLM). For every geometry task:
(1) reference passthrough - a correct program (the oracle's own code + a stdin parser) is run through the SAME render -> sandbox -> output-parse
    path as model programs, on all 8 variants of N instances; anything below 100% is a harness bug (format, parsing, sandbox, timeouts);
(2) metamorphic false alarms - the label-free MR check must accept the reference program on every instance;
(3) input validity - polygons that the prompt calls "simple" are checked for self-intersection.
usage: python sanity_check.py [n_inst]"""
import inspect, random, sys
from concurrent.futures import ThreadPoolExecutor
import run_geo as G
from run_geo_mr import mr_check, run_out

SIZES = {"hull": (10, 20), "area2": (8, 14), "pip": (8, 14), "segs": (6, 10), "close": (10, 20), "convex": (8, 14), "tri": (10, 20),
         "overlap": (8, 14), "lattice": (8, 14), "rectunion": (5, 9), "clip": (6, 10),
         "delaunay": (8, 12), "diameter": (12, 24)}
LIB = "import sys, math\n" + "".join(inspect.getsource(f) + "\n" for f in (
    G.orient, G.hull_count, G.area2, G.on_seg, G.pip, G.seg_inter, G.segs_count, G.closest, G.hull_pts, G.is_convex_poly, G.tri_inside,
    G.polys_overlap, G.lattice_inside, G.rect_union, G.clip_area2, G.fmt_frac, G.in_circle_det, G.in_cc, G.bad_triangles, G.diam2))
D = "d = list(map(int, sys.stdin.read().split()))\n"
PTS = D + "n = d[0]; P = [(d[1 + 2 * i], d[2 + 2 * i]) for i in range(n)]\n"
MAIN = {"diameter": PTS + "print(diam2(P))",
        "delaunay": PTS + "o = 1 + 2 * n; m = d[o]; T = [(d[o+1+3*i], d[o+2+3*i], d[o+3+3*i]) for i in range(m)]\nprint(bad_triangles(P, T))",
        "hull": PTS + "print(hull_count(P))", "close": PTS + "print(closest(P))", "area2": PTS + "print(area2(P))",
        "lattice": PTS + "print(lattice_inside(P))", "convex": PTS + "print(is_convex_poly(P))",
        "pip": PTS + "print(pip(P, (d[1 + 2 * n], d[2 + 2 * n])))",
        "segs": D + "m = d[0]; S = [((d[1+4*i], d[2+4*i]), (d[3+4*i], d[4+4*i])) for i in range(m)]\nprint(segs_count(S))",
        "rectunion": D + "m = d[0]; R = [((d[1+4*i], d[2+4*i]), (d[3+4*i], d[4+4*i])) for i in range(m)]\nprint(rect_union(R))",
        "tri": D + "T = [(d[0], d[1]), (d[2], d[3]), (d[4], d[5])]; n = d[6]; P = [(d[7 + 2 * i], d[8 + 2 * i]) for i in range(n)]\nprint(tri_inside(T, P))",
        "clip": D + "n = d[0]; A = [(d[1+2*i], d[2+2*i]) for i in range(n)]; o = 1 + 2 * n; m = d[o]\n"
                "B = [(d[o+1+2*i], d[o+2+2*i]) for i in range(m)]\nprint(fmt_frac(clip_area2(A, B)))",
        "overlap": D + "n = d[0]; A = [(d[1+2*i], d[2+2*i]) for i in range(n)]; o = 1 + 2 * n; m = d[o]\n"
                   "B = [(d[o+1+2*i], d[o+2+2*i]) for i in range(m)]\nprint(polys_overlap(A, B))"}


def check(task, n_inst):
    code = LIB + MAIN[task]
    ok = tot = mr_fa = nonsimple = 0
    for n in SIZES[task]:
        for i in range(n_inst):
            rng = random.Random(f"{task}-{n}-{i}")
            V = G.variants(task, G.base_instance(task, n, rng), rng)
            for vn, x in V.items():
                tot += 1; ok += run_out(code, task, x) == G.answer(task, x)
            b, bad = mr_check(code, task, V)
            mr_fa += b is None or bool(bad)
            if "poly" in V["identity"]:
                nonsimple += not G.is_simple([tuple(p) for p in V["identity"]["poly"]])
    return task, ok, tot, mr_fa, nonsimple, len(SIZES[task]) * n_inst


if __name__ == "__main__":
    k = int(sys.argv[1]) if len(sys.argv) > 1 else 30
    with ThreadPoolExecutor(10) as ex:
        for task, ok, tot, fa, ns, ni in ex.map(lambda t: check(t, k), [t for t in SIZES if len(sys.argv) < 3 or t in sys.argv[2].split(",")]):
            print(f"{task:10s} reference passthrough {ok}/{tot} | MR false alarms {fa}/{ni} | 'simple' polygons that self-intersect: "
                  + (f"{ns}/{ni}" if task in ("area2", "pip", "convex", "lattice") else "n/a"))
