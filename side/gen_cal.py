"""SIDE-ENV-3 (docs/prereg/PREREG_SIDE.md): scenario generator for side/envs/team_calendar.py in BFCL v4's multi-turn item format.
A team of 5 with 4 rooms (capacities 2-8), 9-14 meetings over three days and 3-6 blocked times. Each conversation has one turn of
each request kind, in random order (each kind is a third of the turns; SIDE-ENV-2's lesson):
  book    a new meeting for 2-4 people at the earliest half-hour start on a day when all are free, in the smallest free room that
          fits (ties: the room name first alphabetically);
  move    an existing meeting (found by title) to another day, at the earliest start when all its attendees are free for its length,
          in the smallest free room that fits;
  cancel  a person's new appointment: cancel every meeting they attend that overlaps it (in id order), then block the time with
          the stated label.
The ground truth is the rule's plan, computed by scanning the half-hour grid (mutating calls only). A request whose plan is empty,
trivial (the earliest slot needs no calendar: 09:00 with everyone free) or impossible is redrawn.
usage: python side/gen_cal.py <out.jsonl> [n=40] [seed=0]"""
import inspect, json, os, random, re, sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from side.envs.team_calendar import DAYS, CalendarAPI, tmin, tstr  # noqa: E402

CLS = "CalendarAPI"
NAMES = ["Ana", "Ben", "Chen", "Dara", "Eli", "Faye", "Gus", "Hana", "Ivo", "Jin", "Kai", "Lena"]
ROOMS = ["Birch", "Cedar", "Elm", "Maple", "Oak", "Pine", "Willow"]
TOPICS = ["Budget review", "Design sync", "Hiring panel", "Roadmap", "Vendor call", "Retro", "Launch prep", "Data audit",
          "Security review", "Offsite plan", "Customer demo", "Code review", "Quarterly goals", "Ops check-in", "Training"]
LABELS = [("see the dentist", "Dentist"), ("pick up a parcel", "Parcel pickup"), ("attend a workshop", "Workshop"),
          ("take a call with the bank", "Bank call"), ("visit the clinic", "Clinic visit"), ("meet a contractor", "Contractor")]


def fdocs():
    tmap = {"str": "string", "int": "integer", "bool": "boolean", "dict": "dict", "list": "array"}
    out = []
    for name, m in inspect.getmembers(CalendarAPI, predicate=inspect.isfunction):
        if name.startswith("_"):
            continue
        doc = inspect.getdoc(m)
        head = doc.split("\n\n")[0].replace("\n", " ")
        args = re.findall(r"^\s*(\w+) \((\w+)\): (.*)$", doc.split("Returns:")[0], re.M)
        rets = re.findall(r"^\s*(\w+) \((\w+)\): (.*)$", doc.split("Returns:")[1], re.M) if "Returns:" in doc else []
        sig = inspect.signature(m)
        req = [a for a, p in sig.parameters.items() if a != "self" and p.default is inspect.Parameter.empty]
        props = {}
        for a, t, d in args:
            props[a] = {"type": tmap.get(t, t), "description": d}
            if t == "list":
                props[a]["items"] = {"type": "string"}
        out.append({"name": name, "description": f"{CalendarAPI()._api_description} Tool description: {head}",
                    "parameters": {"type": "dict", "properties": props, "required": req},
                    "response": {"type": "dict", "properties": {a: {"type": tmap.get(t, t), "description": d} for a, t, d in rets}}})
    return out


def call_str(fn, **kw):
    return f"{fn}(" + ",".join(f"{k}={v!r}" for k, v in kw.items()) + ")"


def earliest(env, people, day, dur, skip=None, need_room=True):
    """the rule's slot: the earliest half-hour start in working hours when every person is free for dur minutes, with the smallest
    free room that fits (ties by name); (start, end, room) or None"""
    rooms = sorted(env.rooms, key=lambda r: (env.rooms[r], r))
    for a in range(9 * 60, 17 * 60 - dur + 1, 30):
        b = a + dur
        if any(env._busy(p, day, a, b, skip=skip) for p in people):
            continue
        for r in rooms:
            if env.rooms[r] >= len(people) and not env._room_busy(r, day, a, b, skip=skip):
                return tstr(a), tstr(b), r
    return None


def scenario(rng, k):
    people = sorted(rng.sample(NAMES, 5))
    rooms = {r: rng.choice([2, 3, 4, 6, 8]) for r in sorted(rng.sample(ROOMS, 4))}
    if max(rooms.values()) < 4:
        rooms[sorted(rooms)[0]] = 6
    env = CalendarAPI()
    env._load_scenario({"people": people, "rooms": rooms, "meetings": [], "blocks": [], "next_id": 1})
    days = sorted(rng.sample(DAYS, 3), key=DAYS.index)
    titles = rng.sample(TOPICS, len(TOPICS))
    for _ in range(rng.randint(9, 14)):
        if not titles:
            break
        att = sorted(rng.sample(people, rng.randint(2, 4))); day = rng.choice(days); dur = rng.choice([30, 60, 60, 90, 120])
        a = rng.randrange(9 * 60, 17 * 60 - dur + 1, 30)
        fit = [r for r in sorted(rooms) if rooms[r] >= len(att)]
        r = rng.choice(fit)
        res = env.book_meeting(titles[-1], day, tstr(a), tstr(a + dur), att, r)
        if "error" not in res:
            titles.pop()
    for _ in range(rng.randint(3, 6)):
        p = rng.choice(people); day = rng.choice(days); a = rng.randrange(9 * 60, 16 * 60 + 1, 30)
        env.block_time(p, day, tstr(a), tstr(a + 30 * rng.randint(1, 2)), rng.choice(["Focus time", "Lunch", "Commute", "Out"]))
    init = {"people": people, "rooms": rooms, "meetings": json.loads(json.dumps(env.meetings)), "blocks": list(env.blocks),
            "next_id": env.next_id}
    kinds = rng.sample(["book", "move", "cancel"], 3)
    turns, gts = [], []
    tie = " (if two rooms are the same size, the one whose name comes first alphabetically)"
    for kind in kinds:
        for _ in range(60):
            if kind == "book" and titles:
                att = sorted(rng.sample(people, rng.randint(2, 4))); day = rng.choice(days); dur = rng.choice([30, 60, 90])
                slot = earliest(env, att, day, dur)
                if not slot or (slot[0] == "09:00" and not any(env._busy(p, day, 540, 540 + dur) for p in att)):
                    continue
                title = titles[-1]
                calls = [call_str("book_meeting", title=title, day=day, start=slot[0], end=slot[1], attendees=att, room=slot[2])]
                msg = rng.choice([f"Book a {dur}-minute meeting '{title}' for {', '.join(att)} on {day}, at the earliest half-hour start "
                                  f"within working hours when all of them are free, in the smallest room that fits them and is free "
                                  f"then{tie}.",
                                  f"Set up '{title}' ({dur} minutes) with {', '.join(att)} on {day}: take the earliest start on the "
                                  f"half hour, inside working hours, that suits everyone, and the smallest free room big enough{tie}."])
                titles.pop()
            elif kind == "move" and env.meetings:
                m = rng.choice(env.meetings); day = rng.choice([d for d in days if d != m["day"]])
                dur = tmin(m["end"]) - tmin(m["start"])
                slot = earliest(env, m["attendees"], day, dur, skip=m["id"])
                if not slot:
                    continue
                calls = [call_str("move_meeting", meeting_id=m["id"], day=day, start=slot[0], end=slot[1], room=slot[2])]
                msg = rng.choice([f"Move '{m['title']}' to {day}, keeping its length: the earliest half-hour start within working hours "
                                  f"when all its attendees are free, in the smallest room that fits them and is free then{tie}.",
                                  f"'{m['title']}' has to move to {day}. Same length, earliest start on the half hour during working "
                                  f"hours that works for every attendee, smallest free room that fits{tie}."])
            elif kind == "cancel":
                p = rng.choice(people); day = rng.choice(days)
                mine = [m for m in env.meetings if p in m["attendees"] and m["day"] == day]
                if not mine:
                    continue
                m0 = rng.choice(mine)
                a = max(9 * 60, tmin(m0["start"]) - 30 * rng.randint(0, 2)); b = min(17 * 60, a + 30 * rng.randint(2, 4))
                over = sorted(m["id"] for m in mine if tmin(m["start"]) < b and a < tmin(m["end"]))
                if not over:
                    continue
                what, label = rng.choice(LABELS)
                calls = [call_str("cancel_meeting", meeting_id=i) for i in over] + [
                    call_str("block_time", person=p, day=day, start=tstr(a), end=tstr(b), label=label)]
                msg = rng.choice([f"{p} has to {what} on {day} from {tstr(a)} to {tstr(b)}. Cancel every meeting {p} attends that "
                                  f"overlaps that time, then block it in {p}'s calendar with the label '{label}'.",
                                  f"On {day}, {tstr(a)}-{tstr(b)}, {p} must {what}. Cancel all of {p}'s meetings overlapping that "
                                  f"window and block the window for {p}, labelled '{label}'."])
            else:
                continue
            res = [eval("env." + c, {"env": env}) for c in calls]
            assert not any("error" in r for r in res), (kind, calls, res)
            turns.append([{"role": "user", "content": msg}]); gts.append(calls)
            break
        else:
            return None
    return {"id": f"side_cal_base_{k}", "cat": "side_cal_base", "initial_config": {CLS: init}, "involved_classes": [CLS],
            "turns": turns, "ground_truth": gts, "kinds": kinds}


def main():
    out, n, seed = sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else 40, int(sys.argv[3]) if len(sys.argv) > 3 else 0
    PD = os.environ.get("POC_DATA", "/home1/leesangjun/SJ/POSTECH/nlp_data")
    s = json.loads(open(f"{PD}/bfcl/mt_items.jsonl").readline())["system"]
    head = s[:s.index("Here is a list of functions in json format that you can invoke.")]
    system = head + "Here is a list of functions in json format that you can invoke.\n" + json.dumps(fdocs(), indent=4) + "\n"
    rng, items, k = random.Random(seed), [], 0
    while len(items) < n:
        try:
            sc = scenario(rng, len(items))
        except AssertionError:
            sc = None
        k += 1
        if sc:
            sc["system"] = system
            items.append(sc)
    with open(out, "w") as f:
        for it in items:
            f.write(json.dumps(it) + "\n")
    print(f"{len(items)} scenarios ({k} drawn) -> {out}; ground-truth calls per turn "
          f"{sum(len(g) for it in items for g in it['ground_truth']) / (3 * len(items)):.2f}; system prompt {len(system)} characters")


if __name__ == "__main__":
    main()
