"""SIDE-ENV: the CPU check a generated environment must pass before any model runs on it. Replays each item's ground truth through BFCL's
own multi-turn checker (as poc/grade_mt.py grades a model): all calls of a turn in one step, then one call per step; both must be valid
for every item. With --negative <old> <new>, also replays the ground truth with a string replaced in every call (a deliberate mistake)
and reports how many items still pass (should be few: a mistake the checker cannot see is a mistake no grade will count).
usage (needs `pip install bfcl-eval==2026.3.23`):
  python side/check_env.py <items.jsonl> <Class=module> [--negative ',as_dependency=True' '']"""
import contextlib, io, json, os, sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from bfcl_eval.constants.executable_backend_config import CLASS_FILE_PATH_MAPPING  # noqa: E402
from bfcl_eval.eval_checker.multi_turn_eval.multi_turn_checker import multi_turn_checker  # noqa: E402


def valid(p, turns, name):
    entry = {"id": p["id"], "initial_config": p["initial_config"], "involved_classes": p["involved_classes"]}
    with contextlib.redirect_stdout(io.StringIO()):
        try:
            return bool(multi_turn_checker(turns, p["ground_truth"], entry, p["cat"], name)["valid"])
        except Exception:
            return False


def main():
    items, cls = sys.argv[1], sys.argv[2]
    for x in cls.split(","):
        CLASS_FILE_PATH_MAPPING[x.split("=")[0]] = x.split("=")[1]
    P = [json.loads(l) for l in open(items)]
    one = sum(valid(p, [[g] for g in p["ground_truth"]], "chk_one") for p in P)
    step = sum(valid(p, [[[c] for c in g] for g in p["ground_truth"]], "chk_step") for p in P)
    print(f"{len(P)} items: ground truth valid {one} (one step per turn), {step} (one call per step)")
    if "--negative" in sys.argv:
        old, new = sys.argv[sys.argv.index("--negative") + 1:][:2]
        neg = sum(valid(p, [[[c.replace(old, new) for c in g]] for g in p["ground_truth"]], "chk_neg") for p in P)
        print(f"with {old!r} -> {new!r} in every call: {neg} of {len(P)} still valid")


if __name__ == "__main__":
    main()
