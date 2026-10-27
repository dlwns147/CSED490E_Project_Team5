"""LC-1 (docs/prereg/PREREG_LC.md): write the code-generation items from LiveCodeBench (livecodebench/code_generation_lite, files
test5.jsonl / test6.jsonl downloaded to $POC_DATA/lcb/raw) to $POC_DATA/lcb/lcb_items.jsonl ({id, platform, date, difficulty, system,
user, fn_name, public: {inputs, outputs}}) and every test (public first, then private, as the official grader orders them) to
lcb_tests.jsonl ({id, fn_name, n_pub, inputs, outputs}). Prompts are LiveCodeBench's own generic chat prompt (lcb_runner/prompts/
code_generation.py: SYSTEM_MESSAGE_GENERIC + get_generic_question_template_answer). Problems dated 2025-01-01 or later only.
The private tests are base64 + zlib + pickle; they are unpickled with an unpickler that refuses every global (the payload is one JSON
string), so a planted object cannot run code. Login node, any python >= 3.8:
  python3.11 -I poc/prep_lcb.py"""
import base64, io, json, os, pickle, zlib

DATA = os.path.join(os.environ.get("POC_DATA", "/home1/leesangjun/SJ/POSTECH/nlp_data"), "lcb")
FROM = "2025-01-01"
SYSTEM = ("You are an expert Python programmer. You will be given a question (problem specification) and will generate a correct "
          "Python program that matches the specification and passes all tests.")
WITH_STARTER = "You will use the following starter code to write the solution to the problem and enclose your code within delimiters."
WITHOUT_STARTER = ("Read the inputs from stdin solve the problem and write the answer to stdout (do not directly test on the sample "
                   "inputs). Enclose your code within delimiters as follows. Ensure that when the python program runs, it reads the "
                   "inputs, runs the algorithm and writes output to STDOUT.")


class _NoGlobals(pickle.Unpickler):
    def find_class(self, module, name):
        raise pickle.UnpicklingError(f"global {module}.{name} refused")


def private_tests(s):
    try:
        return json.loads(s)
    except ValueError:
        return json.loads(_NoGlobals(io.BytesIO(zlib.decompress(base64.b64decode(s.encode("utf-8"))))).load())


def prompt(r):
    p = f"### Question:\n{r['question_content']}\n\n"
    if r["starter_code"]:
        p += f"### Format: {WITH_STARTER}\n```python\n{r['starter_code']}\n```\n\n"
    else:
        p += f"### Format: {WITHOUT_STARTER}\n```python\n# YOUR CODE HERE\n```\n\n"
    return p + "### Answer: (use the provided format with backticks)\n\n"


def main():
    items, n = [], {}
    with open(f"{DATA}/lcb_tests.jsonl", "w") as ft:
        for f in ("test5.jsonl", "test6.jsonl"):
            for l in open(f"{DATA}/raw/{f}"):
                r = json.loads(l)
                if r["contest_date"] < FROM:
                    continue
                pub, priv = json.loads(r["public_test_cases"]), private_tests(r["private_test_cases"])
                fn = json.loads(r["metadata"]).get("func_name") if r["metadata"] else None
                items.append({"id": r["question_id"], "platform": r["platform"], "date": r["contest_date"][:10],
                              "difficulty": r["difficulty"], "system": SYSTEM, "user": prompt(r), "fn_name": fn,
                              "public": {"inputs": [t["input"] for t in pub], "outputs": [t["output"] for t in pub]}})
                ft.write(json.dumps({"id": r["question_id"], "fn_name": fn, "n_pub": len(pub),
                                     "inputs": [t["input"] for t in pub + priv], "outputs": [t["output"] for t in pub + priv]}) + "\n")
                k = (r["platform"], r["difficulty"]); n[k] = n.get(k, 0) + 1
    assert len({x["id"] for x in items}) == len(items)
    with open(f"{DATA}/lcb_items.jsonl", "w") as f:
        f.writelines(json.dumps(x) + "\n" for x in items)
    print(len(items), sorted(n.items()))


if __name__ == "__main__":
    main()
