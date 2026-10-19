// Proposal deck in the default Office look (white, Calibri Light / Calibri, Office accent colours).
const pptxgen = require("pptxgenjs");
const path = require("path");
// optional: writes the theme colours into the deck (from the pptx skill); without it the deck keeps the default Office theme
let applyTheme = async () => {};
try { ({ applyTheme } = require(process.env.PPTX_THEME_JS || "/root/.claude/skills/synced/3c05885e-4c45-4ba8-8aac-398768cdc097_763b3f05-13a5-417f-9a5f-72964acfee24/pptx/scripts/apply_theme.js")); } catch (e) {}

const ROOT = process.env.PROJECT_ROOT || path.join(__dirname, "..");   // repository root (this file is poc/make_slides.js)
const FIG = (f) => path.join(ROOT, "figs", f);
const ICON = (name) => FIG(path.join("icons", name + ".png"));   // figs/icons/*.png, drawn by poc/make_icons.js
const OUT = path.join(ROOT, "PROPOSAL_slides.pptx");

const THEME = {
  name: "Office Theme", headFontFace: "Calibri", bodyFontFace: "Calibri",
  colors: { dk1: "000000", lt1: "FFFFFF", dk2: "44546A", lt2: "E7E6E6", accent1: "4472C4", accent2: "ED7D31", accent3: "A5A5A5",
            accent4: "FFC000", accent5: "5B9BD5", accent6: "70AD47", hlink: "0563C1", folHlink: "954F72" },
};

function newDeck() {   // one pptxgen instance per output file
  const p = new pptxgen();
  p.layout = "LAYOUT_WIDE"; // 13.333 x 7.5, the PowerPoint default
  p.theme = { headFontFace: THEME.headFontFace, bodyFontFace: THEME.bodyFontFace };
  p.title = "Solving Computational Math with LLMs, Accurately and Cheaply";
  p.author = "POSTECH graduate NLP course project";
  const K = p.SchemeColor;
  // ---- layouts modelled on the default template ----
  p.defineSlideMaster({
    title: "Title Slide", background: { color: "FFFFFF" },
    objects: [
      { placeholder: { options: { name: "title", type: "title", x: 1.67, y: 1.4, w: 10.0, h: 2.4, fontSize: 54, align: "center", valign: "bottom", color: K.text1 }, text: "" } },
      { placeholder: { options: { name: "body", type: "body", x: 1.67, y: 4.0, w: 10.0, h: 1.7, fontSize: 22, align: "center", valign: "top", color: K.text1 }, text: "" } },
    ],
  });
  p.defineSlideMaster({
    title: "Title Only", background: { color: "FFFFFF" },
    slideNumber: { x: 12.2, y: 6.95, w: 0.8, h: 0.35, fontSize: 12, color: "8C8C8C", align: "right" },
    objects: [
      { placeholder: { options: { name: "title", type: "title", x: 0.6, y: 0.3, w: 12.1, h: 1.0, fontSize: 36, align: "left", valign: "middle", color: K.text1 }, text: "" } },
    ],
  });
  p.defineSlideMaster({
    title: "Title and Content", background: { color: "FFFFFF" },
    slideNumber: { x: 12.2, y: 6.95, w: 0.8, h: 0.35, fontSize: 12, color: "8C8C8C", align: "right" },
    objects: [
      { placeholder: { options: { name: "title", type: "title", x: 0.6, y: 0.3, w: 12.1, h: 1.0, fontSize: 36, align: "left", valign: "middle", color: K.text1 }, text: "" } },
      { placeholder: { options: { name: "body", type: "body", x: 0.6, y: 1.5, w: 12.1, h: 5.3, fontSize: 18, valign: "top", color: K.text1 }, text: "" } },
    ],
  });
  return p;
}
let pres = newDeck();
const C = pres.SchemeColor;

// ---- helpers ----
const IMG = { fig0: 1.778, fig10: 1.792, fig12: 1.654, fig13: 1.872, fig14: 1.75, fig15: 2.089, fig16: 1.909, fig17: 1.909 };
function img(s, key, file, x, y, w, name) {
  s.addImage({ path: FIG(file), x, y, w, h: w / IMG[key], objectName: name, altText: name });
}
function bullets(s, items, opts) {
  s.addText(items.map((t, i) => ({ text: t, options: { bullet: true, breakLine: i < items.length - 1 } })),
    { isTextBox: true, fontSize: 16, color: C.text1, valign: "top", paraSpaceAfter: 8, margin: 0.05, ...opts });
}
function note(s, text, opts) {
  s.addText(text, { isTextBox: true, fontSize: 12, italic: true, color: C.text2, margin: 0, ...opts });
}
const HDR = (t) => ({ text: t, options: { bold: true, color: "FFFFFF", fill: { color: THEME.colors.accent1 } } });
function table(s, rows, opts) {
  s.addTable(rows, { fontSize: 14, color: C.text1, border: { type: "solid", pt: 0.75, color: "BFBFBF" }, valign: "middle",
                     margin: 0.06, autoPage: false, ...opts });
}
function card(s, x, y, w, h, big, label, body, color, name) {
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w, h, rectRadius: 0.08, fill: { color: "F2F2F2" }, line: { color: "D9D9D9", width: 0.75 }, objectName: name });
  s.addText(big, { isTextBox: true, x: x + 0.25, y: y + 0.2, w: w - 0.5, h: 0.9, fontSize: 30, bold: true, color, margin: 0, fontFace: THEME.headFontFace });
  s.addText(label, { isTextBox: true, x: x + 0.25, y: y + 1.1, w: w - 0.5, h: 0.5, fontSize: 16, bold: true, color: C.text1, margin: 0 });
  s.addText(body, { isTextBox: true, x: x + 0.25, y: y + 1.6, w: w - 0.5, h: h - 1.8, fontSize: 14, color: C.text1, margin: 0, valign: "top" });
}


function caption(s, text) {
  s.addText(text, { isTextBox: true, x: 0.6, y: 6.2, w: 12.1, h: 0.6, fontSize: 20, color: C.text1, align: "center", valign: "middle", margin: 0 });
}
function bigimg(s, key, file, h, name) {   // centred figure of height h starting at y = 1.45
  const w = h * IMG[key];
  s.addImage({ path: FIG(file), x: (13.333 - w) / 2, y: 1.45, w, h, objectName: name, altText: name });
}

function chip(s, t, ok, x, y) {
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: x + 0.25, y, w: 1.7, h: 0.6, rectRadius: 0.1, fill: { color: ok ? "E2F0D9" : "FADBD8" }, line: { color: ok ? THEME.colors.accent6 : "C00000", width: 1 }, objectName: "answer " + t });
  s.addText(t, { isTextBox: true, x: x + 0.25, y, w: 1.7, h: 0.6, fontSize: 22, bold: true, color: ok ? "38761D" : "C00000", align: "center", valign: "middle", margin: 0 });
}

// ---- drawing helpers for example-first slides ----
const GREEN = THEME.colors.accent6, RED = "C00000", BLUE = THEME.colors.accent1, GREY = "F2F2F2";
function panel(s, x, y, w, h, name) {
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w, h, rectRadius: 0.08, fill: { color: GREY }, line: { color: "D9D9D9", width: 0.75 }, objectName: name });
}
function txt(s, t, x, y, w, h, o) {
  s.addText(t, { isTextBox: true, x, y, w, h, fontSize: 16, color: C.text1, margin: 0, valign: "middle", ...o });
}
function code(s, t, x, y, w, h, col, fs = 14) {
  s.addShape(pres.shapes.RECTANGLE, { x, y, w, h, fill: { color: "FFFFFF" }, line: { color: "BFBFBF", width: 0.75 }, objectName: "code " + t.slice(0, 20) });
  s.addText(t, { isTextBox: true, x: x + 0.12, y, w: w - 0.24, h, fontFace: "Courier New", fontSize: fs, color: col || C.text1, margin: 0, valign: "middle" });
}
function arrow(s, x1, y1, x2, y2) {
  s.addShape(pres.shapes.LINE, { x: Math.min(x1, x2), y: Math.min(y1, y2), w: Math.abs(x2 - x1), h: Math.abs(y2 - y1), flipV: y2 < y1,
    line: { color: "7F7F7F", width: 2, endArrowType: "triangle" } });
}
function box(s, t, x, y, w, h, fill, o) {
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w, h, rectRadius: 0.06, fill: { color: fill || "FFFFFF" }, line: { color: "BFBFBF", width: 0.75 }, objectName: "box " + t.slice(0, 20) });
  s.addText(t, { isTextBox: true, x: x + 0.08, y, w: w - 0.16, h, fontSize: 15, color: C.text1, align: "center", valign: "middle", margin: 0, ...o });
}
function hbars(s, x, y, w, rows, rowH, labW = 3.0, valW = 1.5) {   // rows: [label, value 0-100, shown text, colour]
  const barW = w - labW - valW - 0.2;
  rows.forEach(([lab, v, shown, col], k) => {
    const yy = y + k * rowH;
    txt(s, lab, x, yy, labW, rowH * 0.8, { fontSize: 16, align: "right" });
    s.addShape(pres.shapes.RECTANGLE, { x: x + labW + 0.15, y: yy + rowH * 0.15, w: Math.max(0.05, barW * v / 100), h: rowH * 0.5, fill: { color: col }, line: { color: col, width: 0.5 }, objectName: "bar " + lab });
    txt(s, shown, x + labW + 0.25 + barW * v / 100, yy, valW, rowH * 0.8, { fontSize: 18, bold: true, color: col });
  });
}


function prompt(s, title, lines, x, y, w, h, fill) {
  s.addShape(pres.shapes.RECTANGLE, { x, y, w, h, fill: { color: fill }, line: { color: "BFBFBF", width: 0.75 }, objectName: "prompt " + title });
  s.addText([{ text: title, options: { bold: true, fontFace: "Calibri", fontSize: 14, breakLine: true } },
             ...lines.map((l, k) => ({ text: l, options: { breakLine: k < lines.length - 1 } }))],
    { isTextBox: true, x: x + 0.12, y: y + 0.06, w: w - 0.24, h: h - 0.12, fontFace: "Courier New", fontSize: 11.5, color: C.text1, valign: "top", margin: 0 });
}

// 1. Title
let s;
function slideTitle(section, sub, notes) {
s = pres.addSlide({ masterName: "Title Slide", sectionTitle: section });
s.addText([{ text: "Solving Computational Math", options: { fontSize: 44, breakLine: true } },
            { text: "with LLMs, Accurately and Cheaply", options: { fontSize: 40 } }], { placeholder: "title" });
s.addText([
  { text: "A fact, a check, or more thinking: where should the extra effort go?", options: { breakLine: true } },
  { text: sub, options: { fontSize: 16, color: THEME.colors.dk2 } },
], { placeholder: "body" });
s.addNotes(notes);
}
pres.addSection({ title: "Problem" });
slideTitle("Problem", "POSTECH CSED490E (Graduate NLP) · Team 5 · October 2026",
  "Computational math: geometry, optimization, contest problems, word problems whose answer must be computed exactly. We ask how to get them right with the fewest tokens and the smallest GPU.");

// 2. Problem: the four ways an LLM can solve a math problem, and words vs a program on one example
function slideProblem(section, notes) {
s = pres.addSlide({ masterName: "Title Only", sectionTitle: section });
s.addText("How an LLM solves a math problem", { placeholder: "title" });
[["pen", "Answer in words", "it does the arithmetic itself"], ["code", "Write a program", "the computer computes the answer"],
 ["gears", "Call a solver library", "e.g. OR-Tools finds the best routes"], ["brain", "Think longer first", "more hidden notes = more tokens"]].forEach(([icon, head, sub], k) => {
  const x = 0.6 + k * 3.05;
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y: 1.3, w: 2.9, h: 0.85, rectRadius: 0.08, fill: { color: "F2F2F2" }, line: { color: "D9D9D9", width: 0.75 }, objectName: "approach " + head });
  s.addImage({ path: ICON(icon), x: x + 0.15, y: 1.47, w: 0.5, h: 0.5, objectName: "icon " + icon });
  txt(s, [{ text: head, options: { bold: true, fontSize: 16, breakLine: true } }, { text: sub, options: { fontSize: 12.5, color: C.text2 } }], x + 0.75, 1.3, 2.1, 0.85, {});
});
s.addText("Example: one shape moved, turned or flipped, so the right answer never changes: 436 (twice its area)",
  { isTextBox: true, x: 3.9, y: 2.35, w: 8.8, h: 0.4, fontSize: 15, color: C.text1, align: "center", margin: 0 });
s.addImage({ path: FIG("slide2_shapes.png"), x: 4.6, y: 2.75, w: 7.4, h: 1.6, objectName: "four copies of one polygon", altText: "one polygon: original, moved, turned, flipped" });
["original", "moved", "turned", "flipped"].forEach((t, k) => {
  s.addText(t, { isTextBox: true, x: 3.9 + k * 2.2, y: 4.25, w: 2.2, h: 0.3, fontSize: 14, color: C.text2, align: "center", margin: 0 });
});
[["Answer in words", "the model does the arithmetic itself", [["436 ✓", 1], ["2944 ✗", 0], ["392 ✗", 0], ["728 ✗", 0]], 4.7],
 ["Write a program", "the computer does the arithmetic", [["436 ✓", 1], ["436 ✓", 1], ["436 ✓", 1], ["436 ✓", 1]], 5.45]].forEach(([head, sub, ans, y]) => {
  s.addText([{ text: head, options: { bold: true, fontSize: 19, breakLine: true } }, { text: sub, options: { fontSize: 13, color: THEME.colors.dk2 } }],
    { isTextBox: true, x: 0.6, y: y - 0.1, w: 3.2, h: 0.75, valign: "middle", margin: 0, color: C.text1 });
  ans.forEach(([t, ok], k) => chip(s, t, ok, 3.9 + k * 2.2, y));
});
caption(s, "Programs get the arithmetic right, but they can be silently wrong, and thinking is expensive");
s.addNotes(notes);
}
const PROBLEM_NOTES = "Four ways an LLM can solve a math problem: answer in words, write a program, write a program that calls a solver library (for optimization), or think longer first (reasoning mode, more tokens). Example, Qwen3-8B, real outputs. Asked to answer directly, it gives a different area for each copy of the same polygon (only the original is right). Asked for a program, it writes the shoelace formula and the computer gets all copies right. Programs still fail silently, and thinking longer is expensive: on 311 contest problems gpt-oss-120b goes from 57% to 66% for 4.4 times the tokens. Goal: effective (exactly right) and efficient (fewest tokens, smallest GPU).";
slideProblem("Problem", PROBLEM_NOTES);

// 2a. The problems we study, and how hard they are by well-known yardsticks (human contest ranks, exams, classic benchmarks)
function slideKinds(section, title, pre) {
s = pres.addSlide({ masterName: "Title Only", sectionTitle: section });
s.addText(title, { placeholder: "title" });
[["shapes", "Geometry", "How many corners does the rubber band around 10 points have?", "textbook algorithms, exact on every copy", BLUE],
 ["trophy", "Contest problems", "311 Codeforces geometry problems, hidden tests", "Codeforces Master to Grandmaster level", RED],
 ["truck", "Routing, scheduling", "routes for 100 customers with time windows", "classic OR benchmark: a greedy plan is 48% worse", THEME.colors.accent2],
 ["calc", "Word problems", "most coins from 500 gold and 300 wires?", "OR-course exercises (NL4OPT, NeurIPS 2022)", "38761D"],
 ["sqrt", "Math and proofs", "AIME answers; Lean proofs of olympiad statements", "AIME: top ~5% of AMC; IMO gold: 25.9/30", "595959"]].forEach(([icon, head, ex, tag, col], k) => {
  const x = 0.6 + k * 2.45;
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y: 1.3, w: 2.3, h: 2.35, rectRadius: 0.08, fill: { color: "F7F7F7" }, line: { color: "D9D9D9", width: 0.75 }, objectName: "kind " + head });
  s.addImage({ path: ICON(icon), x: x + 0.15, y: 1.42, w: 0.48, h: 0.48, objectName: "icon " + icon });
  txt(s, head, x + 0.7, 1.4, 1.55, 0.55, { fontSize: 15, bold: true });
  txt(s, ex, x + 0.15, 2.0, 2.0, 0.9, { fontSize: 13, valign: "top" });
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: x + 0.1, y: 2.95, w: 2.1, h: 0.6, rectRadius: 0.1, fill: { color: "FFFFFF" }, line: { color: col, width: 1 }, objectName: "tag " + head });
  txt(s, tag, x + 0.15, 2.95, 2.0, 0.6, { fontSize: 12.5, bold: true, color: col, align: "center" });
});
// the contest problems by Codeforces rating, under the human rank at that level
txt(s, "Our 311 contest problems by Codeforces rating, with the human rank at that level", 0.6, 3.8, 12.1, 0.4, { fontSize: 15, bold: true });
const X = (r) => 1.0 + (r - 800) * 11.4 / 2800, BASE = 5.4;
[[800, 1200, "Newbie", "E2F0D9"], [1200, 1600, "Pupil, Specialist", "FFF2CC"], [1600, 2100, "Expert, Cand. Master", "FCE4D6"], [2100, 2400, "Master, Int. Master", "F8CBAD"], [2400, 3600, "Grandmaster and above", "FADBD8"]].forEach(([a, b, lab, fill]) => {
  s.addShape(pres.shapes.RECTANGLE, { x: X(a), y: BASE + 0.05, w: X(b) - X(a), h: 0.38, fill: { color: fill }, line: { color: "FFFFFF", width: 1 }, objectName: "zone " + lab });
  txt(s, lab, X(a), BASE + 0.05, X(b) - X(a), 0.38, { fontSize: 13, bold: true, align: "center" });
});
[[800, 29], [1200, 24], [1600, 59], [2000, 53], [2400, 85], [2800, 40], [3200, 17]].forEach(([r, n]) => {
  const h = 0.8 * n / 85, x = X(r) + 0.08, w = X(r + 400) - X(r) - 0.16;
  s.addShape(pres.shapes.RECTANGLE, { x, y: BASE - h, w, h, fill: { color: r >= 2400 ? RED : "7F7F7F" }, line: { color: "FFFFFF", width: 0.5 }, objectName: "rating " + r });
  txt(s, String(n), x, BASE - h - 0.3, w, 0.28, { fontSize: 13, bold: true, align: "center", color: r >= 2400 ? RED : "404040" });
  txt(s, String(r), X(r) - 0.3, BASE + 0.45, 0.6, 0.25, { fontSize: 11, color: C.text2, align: "center" });
});
txt(s, "3600", X(3600) - 0.3, BASE + 0.45, 0.6, 0.25, { fontSize: 11, color: C.text2, align: "center" });
caption(s, "Median 2200 = Master; 46% at Grandmaster level, where even gpt-oss-120b solves only 48%");
s.addNotes((pre || "") + "How hard, by well-known yardsticks. Contest problems: Codeforces ratings with the human rank at that level (Newbie up to 1199, Pupil 1200-1399, Specialist 1400-1599, Expert 1600-1899, Candidate Master 1900-2099, Master 2100-2299, International Master 2300-2399, Grandmaster 2400+); our median is 2200 (Master) and 142 of 311 are 2400+; 56 problems (18%) are solved by none of our 9 model settings. Routing: the Solomon VRPTW benchmark (1987); a simple greedy plan is valid on all 56 but 47.6% longer than the best known. Word problems: NL4OPT (a NeurIPS 2022 competition) is undergraduate OR-exercise level. Math: AIME invites at least the top 2.5% of AMC 10 and top 5% of AMC 12 takers. Proofs: on IMO-AG-30 an average IMO gold medallist solves 25.9 of 30 and an average participant 15.2 (AlphaGeometry paper). gpt-oss-120b at high effort solves 89% of the easiest contest band and 48% of the 2400+ band.");
}
slideKinds("Problem", "The problems we study, and how hard they are");

// 2b. What goes wrong, why it matters, and what we do
function slideWhy(section, title, pre) {
s = pres.addSlide({ masterName: "Title Only", sectionTitle: section });
s.addText(title, { placeholder: "title" });
function pane(x, head, col, fill) {
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y: 1.35, w: 5.95, h: 3.3, rectRadius: 0.08, fill: { color: fill }, line: { color: col, width: 1 }, objectName: "why " + head });
  txt(s, head, x + 0.25, 1.43, 5.45, 0.5, { fontSize: 21, bold: true, color: col });
}
// 1. a wrong answer with no error, shown as the picture and the two program runs
pane(0.6, "1. Programs fail silently", RED, "FDF2F1");
s.addImage({ path: FIG("slide5_hull.png"), x: 0.8, y: 2.0, w: 1.45, h: 1.45, objectName: "ten points and their hull", altText: "10 points; the rubber band touches 6 of them" });
txt(s, "10 points: 6 corners", 0.65, 3.45, 1.75, 0.3, { fontSize: 12, bold: true, color: GREEN, align: "center" });
s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 2.45, y: 2.0, w: 3.95, h: 1.55, rectRadius: 0.05, fill: { color: "262626" }, line: { color: "262626" }, objectName: "terminal" });
s.addText([
  { text: "$ python hull_A.py   # task only", options: { color: "BFBFBF", breakLine: true } },
  { text: "6", options: { color: "8FD16A", bold: true, breakLine: true } },
  { text: "$ python hull_B.py   # + 8 helpers", options: { color: "BFBFBF", breakLine: true } },
  { text: "0    ← no error, just wrong", options: { color: "FF7B7B", bold: true } },
], { isTextBox: true, x: 2.6, y: 2.05, w: 3.7, h: 1.45, fontFace: "Courier New", fontSize: 12.5, valign: "middle", margin: 0 });
s.addImage({ path: ICON("warn"), x: 0.85, y: 3.93, w: 0.35, h: 0.35, objectName: "warning icon" });
txt(s, "The problem's own examples miss it too: \"Find Color\" passes all 3, then fails hidden test 11", 1.3, 3.85, 5.1, 0.6, { fontSize: 13 });
// 2. more thinking costs many more tokens; one page ≈ 700 tokens
pane(6.75, "2. Thinking longer is expensive", THEME.colors.accent2, "FDF0E6");
txt(s, "tokens per contest problem (gpt-oss-120b); one page ≈ 700 tokens", 7.0, 1.95, 5.5, 0.3, { fontSize: 12.5, color: C.text2 });
[["medium effort", "57% solved", 10, "page", 2.35], ["high effort", "66% solved", 43, "pagehot", 2.9]].forEach(([lab, acc, n, icon, y]) => {
  txt(s, [{ text: lab, options: { bold: true, breakLine: true } }, { text: acc }], 7.0, y, 1.55, 0.5, { fontSize: 13 });
  for (let k = 0; k < n; k++) {
    s.addImage({ path: ICON(icon), x: 8.6 + (k % 20) * 0.195, y: y + Math.floor(k / 20) * 0.24, w: 0.19, h: 0.22, objectName: `${lab} page ${k}` });
  }
});
txt(s, [{ text: "4.4× the pages", options: { bold: true, fontSize: 22, color: THEME.colors.accent2 } }, { text: "  for only 9 more points", options: { fontSize: 15 } }],
    7.0, 3.85, 5.5, 0.6, { valign: "middle" });
// why it matters
[["robot", "agents already write this code"], ["coins", "tokens cost money and time"], ["gpu", "most teams have one 24 GB GPU"]].forEach(([icon, t], k) => {
  const x = 0.6 + k * 4.1;
  box(s, "", x, 4.82, 3.9, 0.55, "F2F2F2");
  s.addImage({ path: ICON(icon), x: x + 0.15, y: 4.88, w: 0.42, h: 0.42, objectName: "icon " + icon });
  txt(s, t, x + 0.7, 4.82, 3.1, 0.55, { fontSize: 15 });
});
// the question, with the three options
s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 0.6, y: 5.55, w: 12.1, h: 1.05, rectRadius: 0.08, fill: { color: "DEEBF7" }, line: { color: "BDD7EE", width: 0.75 }, objectName: "our question" });
txt(s, "Where should extra effort go?", 0.85, 5.6, 4.4, 0.95, { fontSize: 20, bold: true, color: BLUE });
[["fact", "a missing fact", "E2F0D9", "38761D"], ["check", "a free check", "E2F0D9", "38761D"], ["brain", "more thinking", "FADBD8", RED]].forEach(([icon, t, fill, col], k) => {
  const x = 5.3 + k * 2.45;
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y: 5.8, w: 2.3, h: 0.55, rectRadius: 0.2, fill: { color: fill }, line: { color: col, width: 1 }, objectName: "option " + t });
  s.addImage({ path: ICON(icon), x: x + 0.14, y: 5.89, w: 0.36, h: 0.36, objectName: "icon " + icon });
  txt(s, t, x + 0.62, 5.8, 1.65, 0.55, { fontSize: 16, bold: true, color: col });
});
s.addNotes((pre || "") + "Two problems. (1) Programs fail silently: for the same task (how many corners does the rubber band around these 10 points have?) Qwen3-14B's program prints 6 with only the task, and 0 when the prompt also offers 8 unneeded helper functions, with no error message. Even the examples in a contest problem miss such bugs: a program for 'Find Color' passes all 3 and fails hidden test 11; 24-37% of gpt-oss-120b's wrong contest programs pass the examples. (2) Thinking longer is expensive: on 311 Codeforces geometry problems gpt-oss-120b uses 6.8k tokens per problem at medium effort (about 10 pages) and solves 57%, and 30k tokens at high effort (about 43 pages) for 66%: 4.4 times the tokens for 9 more points. Why it matters: agents already write route planners, schedulers and geometry code; tokens are cost and latency; most teams have one small GPU. Our question: where should extra effort go, a missing fact, a free check, or more thinking? We test each on geometry, routing, scheduling, contest problems, word problems, math and proofs, counting accuracy and tokens.");
}
slideWhy("Problem", "What goes wrong, and what we do");

// 3. Words
function slideWords(section, title, pre) {   // pre: text put before the speaker notes
s = pres.addSlide({ masterName: "Title Only", sectionTitle: section });
s.addText(title, { placeholder: "title" });
[["Program", "code the model writes; the computer runs it", "the shoelace formula for an area"],
 ["Tool", "ready-made code we put in the prompt", "orient(a, b, c); the OR-Tools route library"],
 ["Fact", "know-how the model may lack", "the exact function name to call"],
 ["Check", "a cheap test, without knowing the answer", "run the examples printed in the problem"],
 ["Thinking", "hidden notes before answering; costs tokens", "low / medium / high effort"],
 ["Token", "a piece of a word: the unit of cost", "a one-page answer ≈ 700 tokens"]].forEach(([w, d, e], i) => {
  const x = 0.6 + (i % 3) * 4.15, y = 1.55 + Math.floor(i / 3) * 2.45;
  panel(s, x, y, 3.85, 2.2, "term " + w);
  txt(s, w, x + 0.25, y + 0.15, 3.35, 0.6, { fontSize: 26, bold: true, color: BLUE });
  txt(s, d, x + 0.25, y + 0.78, 3.35, 0.7, { fontSize: 16, valign: "top" });
  txt(s, "e.g. " + e, x + 0.25, y + 1.5, 3.35, 0.55, { fontSize: 14, italic: true, color: C.text2, valign: "top" });
});
s.addNotes((pre || "") + "Plain definitions for the rest of the talk. Every result is reported as accuracy and tokens (cost).");
}
slideWords("Problem", "Words we use");

pres.addSection({ title: "Findings" });
// 4b. Results at a glance
function slideGlance(section, title, pre) {   // pre: text put before the speaker notes
s = pres.addSlide({ masterName: "Title Only", sectionTitle: section });
s.addText(title, { placeholder: "title" });
txt(s, [{ text: "blue", options: { bold: true, color: BLUE } }, { text: " = the better way   ·   " },
        { text: "grey", options: { bold: true, color: "7F7F7F" } }, { text: " = the usual way or a published method   ·   " },
        { text: "red", options: { bold: true, color: RED } }, { text: " = makes it worse" }], 0.6, 1.3, 12.1, 0.35, { fontSize: 14, color: C.text2 });
function mini(s, k, title, sub, rows) {
  const x0 = 0.6 + (k % 3) * 4.15, y0 = 1.85 + Math.floor(k / 3) * 2.6;
  txt(s, title, x0, y0, 3.95, 0.38, { fontSize: 17, bold: true });
  txt(s, sub, x0, y0 + 0.38, 3.95, 0.3, { fontSize: 12, color: C.text2 });
  rows.forEach(([lab, v, shown, col], r) => {
    const y = y0 + 0.78 + r * 0.42;
    txt(s, lab, x0, y, 1.55, 0.36, { fontSize: 13, align: "right" });
    s.addShape(pres.shapes.RECTANGLE, { x: x0 + 1.62, y: y + 0.05, w: Math.max(0.03, 1.25 * v / 100), h: 0.26, fill: { color: col }, line: { color: col, width: 0.5 }, objectName: `${title} ${lab}` });
    txt(s, shown, x0 + 1.68 + 1.25 * v / 100, y, 1.15, 0.36, { fontSize: 13, bold: true, color: col === "A5A5A5" ? "595959" : col });
  });
}
const G = "A5A5A5";
mini(s, 0, "Add the missing fact", "delivery routing, Qwen3-32B: % optimal",
     [["task only", 23, "23%", G], ["think longer", 3, "3%", RED], ["whole manual", 7, "7%", RED], ["5 exact lines", 83, "77–90%", BLUE]]);
mini(s, 1, "Small models gain most", "word problems: % solved",
     [["Qwen3-1.7B", 0.1, "0%", G], ["1.7B + fact", 44.5, "45%", BLUE], ["Qwen3-32B", 65.4, "65%", G], ["32B + fact", 66.2, "66%", BLUE]]);
mini(s, 2, "Compare two versions", "geometry, Qwen3-32B: % · tokens",
     [["8 extra tools", 59, "59% · 0.6k", RED], ["always think", 98, "98% · 5.9k", G], ["think if differ", 99, "99% · 4.3k", BLUE]]);
mini(s, 3, "Think only on failure", "311 contest problems: % · tokens",
     [["always high", 66.2, "66% · 30k", G], ["high on failure", 66.3, "66% · 25k", BLUE]]);
mini(s, 4, "Reuse a checked program", "48 routing days: % valid · tokens",
     [["new each day", 7, "7% · 86k", G], ["own notes (DC)", 36, "31–40%", G], ["reuse one", 94, "94% · 28k", BLUE]]);
mini(s, 5, "All together", "624 problems, 3 models: % · tokens",
     [["think on hardest", 74, "74% · 4.1k", G], ["fix by type", 83, "83% · 4.2k", G], ["fact first", 87, "87% · 2.5k", BLUE]]);
s.addNotes((pre || "") + "One panel per result. Add the fact: routing 23% to 77-90% (thinking longer 3%, whole manual 7%). Small models gain most: Qwen3-1.7B 0% to 45%, Qwen3-32B 65% to 66% (word problems). Compare two versions: 99% at 4.3k tokens vs always thinking 98% at 5.9k; with 8 extra tools 59%. Think only on a failed check (gpt-oss-120b, contest): 66.3% at 24.7k vs 66.2% at 30.1k. Reuse: 94% of 48 routing days vs 7% with a new program per day; Dynamic Cheatsheet (DC, the model's own notes) 31-40%. All together: fact first then think on failure 87% at 2.5k vs 74% at 4.1k for thinking on the hardest-looking problems (Snell-style) and 83% for choosing the fix by failure type.");
}
slideGlance("Findings", "Findings at a glance: same or better, for fewer tokens");

// 5. Step 2: fact
// 4. Missing knowledge
function slideFact(section, title, pre) {   // pre: text put before the speaker notes
s = pres.addSlide({ masterName: "Title Only", sectionTitle: section });
s.addText(title, { placeholder: "title" });
txt(s, "Task: plan delivery routes for trucks with a weight limit, using Google's OR-Tools library (Qwen3-32B)", 0.6, 1.4, 12.1, 0.45, { fontSize: 18 });
prompt(s, "Prompt A: task + a long OR-Tools reference sheet", ["...the task...", "RoutingModel: AddDimension(...), Solve(...),", "SetArcCostEvaluator(...), ... (many functions)"], 0.6, 1.95, 5.0, 1.15, "FCE4D6");
arrow(s, 5.6, 2.52, 6.0, 2.52);
code(s, "RegisterUnaryLongLivingCallback(...)", 6.0, 2.25, 4.6, 0.55, RED, 12);
txt(s, "✗ crash: no such function", 10.75, 2.15, 2.0, 0.75, { fontSize: 15, bold: true, color: RED });
prompt(s, "Prompt B: task + 5 lines of exact usage", ["...the task...", "dcb = r.RegisterUnaryTransitCallback(demand)", "r.AddDimensionWithVehicleCapacity(dcb, ...)"], 0.6, 3.3, 5.0, 1.15, "E2F0D9");
arrow(s, 5.6, 3.87, 6.0, 3.87);
code(s, "RegisterUnaryTransitCallback(...)", 6.0, 3.6, 4.6, 0.55, GREEN, 12);
txt(s, "✓ runs, best route", 10.75, 3.5, 2.0, 0.75, { fontSize: 15, bold: true, color: GREEN });
txt(s, "Out of 100 routing problems, how many it solves best:", 0.6, 4.65, 12.1, 0.4, { bold: true, fontSize: 17 });
hbars(s, 0.6, 5.05, 12.1, [["Nothing extra", 23, "23", "7F7F7F"], ["Think longer", 3, "3", RED], ["Long reference sheet", 7, "7", RED], ["5 exact lines", 83, "77–90", GREEN]], 0.38);
s.addNotes((pre || "") + "The model writes the program (the right side shows the line that matters). With a long reference sheet it guesses a plausible function name that does not exist and crashes; with five lines showing the exact call it writes the right one. Thinking longer cannot supply a fact it does not have (3 of 100). On the 56 standard Solomon routing problems, three such facts together take gpt-oss-120b to a valid plan on every instance.");
}
slideFact("Findings", "Finding 1: give the fact, not the manual");

// 5b. Small models
function slideSmall(section, title, pre) {   // pre: text put before the speaker notes
s = pres.addSlide({ masterName: "Title Only", sectionTitle: section });
s.addText(title, { placeholder: "title" });
txt(s, "Word problems → optimization programs (NL4OPT + IndustryOR, 345 problems, 3 runs): % solved", 0.6, 1.35, 12.1, 0.45, { fontSize: 18 });
s.addChart(pres.charts.BAR, [
  { name: "program only", labels: ["Qwen3-1.7B", "Qwen3-4B", "Qwen3-8B", "Qwen3-14B (4-bit)", "Qwen3-32B (4-bit)"], values: [0.1, 14.7, 34.3, 58.1, 65.4] },
  { name: "+ 6 lines of exact solver usage", labels: ["Qwen3-1.7B", "Qwen3-4B", "Qwen3-8B", "Qwen3-14B (4-bit)", "Qwen3-32B (4-bit)"], values: [44.5, 46.0, 51.7, 66.0, 66.2] },
], { x: 0.6, y: 1.85, w: 8.2, h: 4.2, barDir: "col", barGrouping: "clustered", chartColors: ["A5A5A5", THEME.colors.accent1],
     showValue: true, dataLabelPosition: "outEnd", dataLabelFormatCode: "0", dataLabelFontSize: 12, dataLabelFontFace: "+mn-lt",
     valAxisMaxVal: 80, valAxisMinVal: 0, valAxisLabelFontSize: 12, valAxisLabelFontFace: "+mn-lt", valAxisLabelColor: "595959",
     catAxisLabelFontSize: 13, catAxisLabelFontFace: "+mn-lt", catAxisLabelColor: "404040",
     valGridLine: { color: "E7E6E6", size: 0.75 }, catGridLine: { style: "none" },
     showLegend: true, legendPos: "t", legendFontSize: 13, legendFontFace: "+mn-lt", objectName: "fact gain by model size" });
[["+44", "Qwen3-1.7B"], ["+31", "Qwen3-4B"], ["+17", "Qwen3-8B"], ["+8", "Qwen3-14B"], ["+1", "Qwen3-32B"]].forEach(([g, m], k) => {
  txt(s, g, 9.2, 1.95 + k * 0.62, 1.0, 0.5, { fontSize: 22, bold: true, color: BLUE, align: "right" });
  txt(s, m, 10.35, 1.95 + k * 0.62, 2.4, 0.5, { fontSize: 15 });
});
txt(s, "fact gain (points)", 9.2, 5.1, 3.5, 0.4, { fontSize: 13, color: C.text2 });
caption(s, "With the fact, a model on one 24 GB GPU matches Qwen3-32B (73% vs 72%) at 1/8 of the tokens");
s.addNotes((pre || "") + "SIZE study. Without the snippet the 1.7B model invents OR-Tools attributes and almost never runs (0.1%); with six lines of exact usage it solves 44.5%. The gain shrinks as the model grows (+44, +31, +17, +8, +1 points). With the recipe (fact first, think only when the check fails), models that fit one 24 GB GPU match or beat Qwen3-32B: gpt-oss-20b 73.0% at 0.7k tokens vs Qwen3-32B with the fact and always thinking 72.0% at 5.5k; on the optimization suite Qwen3-14B (4-bit) 87-92% vs Qwen3-32B 79-85%. Below 14B the optimization suite stays at 47% or less.");
}
slideSmall("Findings", "Finding 2: one fact helps small models most");

// 5. Steering
function slideTwoVersions(section, title, pre) {   // pre: text put before the speaker notes
s = pres.addSlide({ masterName: "Title Only", sectionTitle: section });
s.addText(title, { placeholder: "title" });
txt(s, "Extra tools can mislead the model. Write the program with and without them, and compare:", 0.6, 1.4, 12.1, 0.45, { fontSize: 18 });
s.addImage({ path: FIG("slide5_hull.png"), x: 0.75, y: 1.95, w: 2.05, h: 2.05, objectName: "ten points and their hull", altText: "10 points; the rubber band touches 6 of them" });
txt(s, "rubber band around 10 points: 6 corners", 0.4, 4.0, 2.75, 0.4, { fontSize: 12, bold: true, color: GREEN, align: "center" });
prompt(s, "Prompt A: only the task", ["Points: (20,-40) (-26,-18) ...", "How many corners does the rubber", "band have? Write a Python program."], 3.55, 1.95, 4.1, 1.0, "FFFFFF");
arrow(s, 7.65, 2.45, 8.1, 2.45);
chip(s, "6 ✓", true, 7.9, 2.15);
prompt(s, "Prompt B: the task + 8 helpers", ["...same task...", "You may use these helpers:", "orient(a, b, c)    # side of a line", "polar_sort(pts, o) # sort by angle", "... and 6 more"], 3.55, 3.1, 4.1, 1.38, "FCE4D6");
arrow(s, 7.65, 3.72, 8.1, 3.72);
chip(s, "0 ✗", false, 7.9, 3.42);
txt(s, "used polar_sort: wrong method", 8.0, 4.05, 2.2, 0.35, { fontSize: 12, color: C.text2, align: "center" });
arrow(s, 9.9, 2.45, 10.35, 2.9); arrow(s, 9.9, 3.72, 10.35, 3.3);
box(s, "answers differ → think it through → 6 ✓", 10.35, 2.45, 2.35, 1.3, "DEEBF7", { fontSize: 15 });
txt(s, "Over 108 geometry problems (Qwen3-32B, 3 runs): how often the answer is right, and tokens per problem", 0.6, 4.6, 12.1, 0.4, { bold: true, fontSize: 17 });
hbars(s, 0.6, 5.0, 12.1, [["Always Prompt B (+ helpers)", 59, "59% · 0.6k", RED],
                          ["Always Prompt A (task only)", 77, "77% · 0.4k", "7F7F7F"],
                          ["Always think long", 98, "98% · 5.9k", "7F7F7F"],
                          ["Both prompts, think only if they differ", 99, "99% · 4.3k", BLUE]], 0.4, 4.1, 1.9);
s.addNotes((pre || "") + "The example (Qwen3-14B, real output): the only difference between the two prompts is the toolbox, eight correct helper functions that the task does not need. We run the two finished programs ourselves. Program A prints 6, the right answer; program B builds its method on polar_sort and prints 0. The bars (Qwen3-32B, 108 generated geometry problems, mean of 3 runs; tokens = output tokens per problem, both cheap programs counted for the last row): with the helpers 59%, task only 77%, always thinking 98% at 5.9k tokens, and writing both cheap programs and thinking only when their answers differ 99% at 4.3k (27% fewer tokens; the pair differs on 37-53% of problems). It does not help when both programs share the mistake (gpt-oss-120b on contest problems).");
}
slideTwoVersions("Findings", "Finding 3: two versions catch each other's mistakes");

// 6. Hard problems
function slideHard(section, title, pre) {   // pre: text put before the speaker notes
s = pres.addSlide({ masterName: "Title Only", sectionTitle: section });
s.addText(title, { placeholder: "title" });
txt(s, "Every contest problem lists a few sample inputs with the correct outputs. Running the program on them costs nothing:", 0.6, 1.4, 12.1, 0.45, { fontSize: 18 });
box(s, "write a program quickly (medium effort)", 0.6, 2.2, 2.9, 0.85, "FFFFFF");
arrow(s, 3.5, 2.62, 3.95, 2.62);
box(s, "run it on the examples", 3.95, 2.2, 2.4, 0.85, "DEEBF7");
arrow(s, 6.35, 2.45, 6.85, 2.25); arrow(s, 6.35, 2.8, 6.85, 3.07);
box(s, "all right → submit", 6.85, 1.97, 2.7, 0.56, "E2F0D9");
box(s, "one wrong → think harder (high effort), then submit", 6.85, 2.77, 4.2, 0.6, "FADBD8");
function caseCard(s, x, name, lines, col, fill) {
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y: 3.65, w: 5.9, h: 1.5, rectRadius: 0.08, fill: { color: fill }, line: { color: col, width: 1 }, objectName: "case " + name });
  txt(s, name, x + 0.2, 3.73, 5.5, 0.45, { fontSize: 17, bold: true });
  txt(s, lines, x + 0.2, 4.18, 5.5, 0.95, { fontSize: 15, valign: "top" });
}
caseCard(s, 0.6, "\"Make a triangle!\" (easy)", "Q: how many cm to add so 3 sticks make a triangle?\nsamples (3,4,5) → 0 and (2,5,3) → 1: program agrees ✓\n→ submit; correct, no extra tokens", GREEN, "F3F9EF");
caseCard(s, 6.8, "\"Arrow\" (hard)", "Q: print the 7 corners of an arrow shape\nprogram's corners ≠ the sample ✗ → think harder → correct ✓\n4k + 13k tokens, paid only because the check failed", RED, "FDF2F1");
txt(s, "Over 311 problems (gpt-oss-120b): same 66% solved as always thinking hard, 18% fewer tokens", 0.6, 5.35, 12.1, 0.45, { fontSize: 17, bold: true });
hbars(s, 0.6, 5.8, 9.5, [["Always think hard", 100, "30k tokens", "7F7F7F"], ["Think hard only on a failed check", 82, "25k tokens", BLUE]], 0.4, 3.6);
s.addNotes((pre || "") + "Real gpt-oss-120b runs on Codeforces geometry problems. The examples are a free check: if the quick (medium-effort) program gets them right we submit it; if not, we pay for high effort. Examples can miss bugs (Find Color passed all 3 examples and failed hidden test 11), so the full policy also runs a quick brute-force comparison on small inputs. Result: 66.3% at 24.7k tokens per problem vs 66.2% at 30.1k for always high effort.");
}
slideHard("Findings", "Finding 4: think harder only when a check fails");

// 7. Pay once
function slideReuse(section, title, pre) {   // pre: text put before the speaker notes
s = pres.addSlide({ masterName: "Title Only", sectionTitle: section });
s.addText(title, { placeholder: "title" });
txt(s, "A delivery company plans routes every day: the same kind of problem, new customers each day (gpt-oss-120b)", 0.6, 1.4, 12.1, 0.45, { fontSize: 18 });
function days(s, y, good, label, res, col) {
  txt(s, label, 0.6, y, 3.4, 1.3, { fontSize: 17, bold: true });
  for (let k = 0; k < 48; k++) {
    const cx = 4.1 + (k % 16) * 0.33, cy = y + Math.floor(k / 16) * 0.42;
    const ok = k < good;
    s.addShape(pres.shapes.RECTANGLE, { x: cx, y: cy, w: 0.27, h: 0.34, fill: { color: ok ? GREEN : "FADBD8" }, line: { color: ok ? GREEN : "E6B8B7", width: 0.5 }, objectName: `${label} day ${k}` });
  }
  txt(s, res, 9.6, y, 3.1, 1.3, { fontSize: 17, bold: true, color: col });
}
days(s, 2.15, 3, "A: ask for a new program every day", "valid on 7% of days\n≈ 86k tokens", RED);
days(s, 3.85, 45, "B: the model writes 16 programs; keep the one valid on 8 past days; reuse it", "valid on 94% of days\n28k tokens in total", "38761D");
txt(s, "each square = one of 48 new days · green = a valid route plan", 4.1, 5.25, 8.6, 0.4, { fontSize: 14, color: C.text2 });
txt(s, "Only the data change, so one checked program keeps working (also on 4× bigger days). New rule? Ask the model to edit it.", 0.6, 5.85, 12.1, 0.6, { fontSize: 17 });
s.addNotes((pre || "") + "Analogy for the 56 Solomon routing problems: each problem is like one day's orders. A: a new program per day is valid on 6 and 1 of 48 days in two runs (7%; drawn as 3), about 1.8k tokens each. B: draw 16 programs once, keep the one that gives valid plans on 8 practice days, reuse it: valid on 45 of 48 days (94%), 28k tokens in total. Reused programs also work on 200- and 400-customer problems; for a new rule (job-shop with release dates) editing the working program beats writing a new one (10% to 68-100%).");
}
slideReuse("Findings", "Finding 5: repeated problems need one checked program");

// 7b. Finding 6: automatic facts
function slideAuto(section, title, pre) {   // pre: text put before the speaker notes
s = pres.addSlide({ masterName: "Title Only", sectionTitle: section });
s.addText(title, { placeholder: "title" });
txt(s, "Example (Qwen3-8B, MAMO): products X, Y, Z cost $10, $15, $20; X+Y ≤ 5000, Y+Z ≤ 4000, X+Z ≥ 2000. Minimum cost? (20000)", 0.6, 1.3, 12.1, 0.45, { fontSize: 16 });
txt(s, "No fact", 0.6, 1.85, 6.7, 0.35, { fontSize: 15, bold: true });
code(s, "solver.Objective().Minimize()", 0.6, 2.2, 4.4, 0.5, RED, 13);
txt(s, "✗ crash: no such method", 5.15, 2.2, 2.2, 0.5, { fontSize: 14, bold: true, color: RED });
prompt(s, "The fact: its own program for another problem (vans and trucks) that passed the free check", [
  "solver = pywraplp.Solver.CreateSolver('SCIP')", "v = solver.IntVar(0, solver.infinity(), 'v')", "solver.Minimize(v)", "status = solver.Solve()"], 0.6, 2.9, 6.7, 1.45, "E2F0D9");
txt(s, "With the fact (written twice; both agree, so no thinking)", 0.6, 4.5, 6.7, 0.35, { fontSize: 15, bold: true });
code(s, "solver.Minimize(10*x + 15*y + 20*z)", 0.6, 4.85, 4.4, 0.5, GREEN, 13);
txt(s, "✓ 20000 · 0.6k tokens (thinking: 5.3k)", 5.15, 4.85, 2.4, 0.5, { fontSize: 13, bold: true, color: GREEN });
s.addChart(pres.charts.BAR, [
  { name: "no fact", labels: ["gpt-oss-20b", "Qwen3-14B", "Qwen3-8B"], values: [73.2, 59.7, 45.5] },
  { name: "hand-written", labels: ["gpt-oss-20b", "Qwen3-14B", "Qwen3-8B"], values: [78.9, 71.4, 72.0] },
  { name: "automatic", labels: ["gpt-oss-20b", "Qwen3-14B", "Qwen3-8B"], values: [78.8, 71.7, 71.0] },
], { x: 7.7, y: 1.85, w: 5.0, h: 3.6, barDir: "col", barGrouping: "clustered", chartColors: ["A5A5A5", "7F7F7F", THEME.colors.accent1],
     showValue: true, dataLabelPosition: "outEnd", dataLabelFormatCode: "0", dataLabelFontSize: 11, dataLabelFontFace: "+mn-lt",
     valAxisMaxVal: 100, valAxisMinVal: 0, valAxisLabelFontSize: 10, valAxisLabelFontFace: "+mn-lt", valAxisLabelColor: "595959",
     catAxisLabelFontSize: 12, catAxisLabelFontFace: "+mn-lt", catAxisLabelColor: "404040",
     valGridLine: { color: "E7E6E6", size: 0.75 }, catGridLine: { style: "none" },
     showLegend: true, legendPos: "t", legendFontSize: 12, legendFontFace: "+mn-lt",
     showTitle: true, title: "MAMO, 863 problems never used before: % solved", titleFontSize: 13, titleFontFace: "+mn-lt", titleColor: "404040",
     objectName: "automatic fact on held-out MAMO" });
txt(s, "Does not work: a program of a different problem type (−14 to −21 points); a list of the library's names (66% → 56%)", 7.7, 5.5, 5.0, 0.6, { fontSize: 13, color: RED, valign: "top" });
caption(s, "No human writes the fact: the model's own checked program shows the right call");
s.addNotes((pre || "") + "Real outputs, Qwen3-8B on MAMO easy-189 (gold 20000). Without a fact it writes solver.Objective().Minimize() and crashes (AttributeError). The fact is chosen automatically: its own shortest program from NL4OPT (a vans-and-trucks problem) that passed the label-free check (it runs and prints a value); no answers, no human. With it, both programs write solver.Minimize(10*x + 15*y + 20*z) and print 20000 (316 + 312 tokens), they agree, so no thinking is needed (thinking alone: 5,323 tokens). Chart: on the held-out MAMO the automatic fact matches the hand-written one (gpt-oss-20b within 1.2 points on 3 seeds). It stays within a problem family: a program of another problem type is 14-21 points below the hand-written fact on the optimization suite, and an introspected list of names hurts (Qwen3-32B 66.2 to 56.1%).");
}
slideAuto("Findings", "Finding 6: the fact can be found without a human");

// 7c. Finding 7: proofs
function slideProof(section, title, pre) {   // pre: text put before the speaker notes
s = pres.addSlide({ masterName: "Title Only", sectionTitle: section });
s.addText(title, { placeholder: "title" });
txt(s, "Example (miniF2F): show that if x < 100 and 9x mod 100 = 1, then x = 89", 0.6, 1.3, 6.6, 0.45, { fontSize: 16 });
code(s, "theorem (x : ℕ) (h₀ : x < 100) (h₁ : x * 9 % 100 = 1) : x = 89", 0.6, 1.8, 6.6, 0.5, null, 12);
txt(s, "General model (Qwen3-32B)", 0.6, 2.45, 6.6, 0.35, { fontSize: 15, bold: true });
code(s, "... Nat.ModEq_iff_modEq ...", 0.6, 2.8, 3.6, 0.5, RED, 13);
txt(s, "✗ no such lemma in the library", 4.35, 2.8, 2.9, 0.5, { fontSize: 14, bold: true, color: RED });
txt(s, "Specialized prover (Goedel-Prover-V2-8B)", 0.6, 3.45, 6.6, 0.35, { fontSize: 15, bold: true });
code(s, "interval_cases x <;> norm_num at h₁ ⊢ <;> omega", 0.6, 3.8, 5.2, 0.5, GREEN, 12);
txt(s, "✓ tries all 100 x", 5.9, 3.8, 1.5, 0.5, { fontSize: 14, bold: true, color: GREEN });
txt(s, "244 statements, 8 tries each: % proved", 7.6, 1.3, 5.1, 0.45, { fontSize: 15, bold: true });
hbars(s, 7.6, 1.8, 5.1, [["Qwen3-32B", 12.7, "13%", "A5A5A5"], ["gpt-oss-20b", 27.0, "27%", "A5A5A5"], ["Qwen3.6-35B", 54.5, "55%", "A5A5A5"],
                         ["DeepSeek-Prover-7B", 67.6, "68%", "5B9BD5"], ["Goedel-Prover-8B", 73.8, "74%", BLUE]], 0.5, 2.0, 0.75);
txt(s, "For general models no step helps: a similar verified proof 133 → 133 · thinking 133 → 129 · an inequality fact sheet 24 → 21; fixing a proof from Lean's errors works half as well as a fresh try",
    0.6, 4.6, 12.1, 0.7, { fontSize: 15 });
txt(s, "Geometry proofs (AlphaGeometry's solver + LLM-proposed points): IMO 12 → 13 of 30 (only 2014 P4: \"take the midpoint of BC\"); easier JGEX 187 → 200 of 231",
    0.6, 5.35, 12.1, 0.7, { fontSize: 15 });
caption(s, "The missing piece is a skill, not a fact: use a specialized 8B prover (fits one 24 GB GPU)");
s.addNotes((pre || "") + "Real outputs. miniF2F mathd_numbertheory_34 (9^-1 mod 100 = 89). Qwen3-32B's 8 attempts all fail; they cite lemmas that do not exist, e.g. Nat.ModEq_iff_modEq. Goedel-Prover-V2-8B proves it by checking every x below 100 (interval_cases, then norm_num and omega). Specialized provers rarely invent names (6-7% of failed attempts vs 22-40%). For general models a verified proof of the most similar statement, thinking, or an inequality toolkit does not help; even for provers, revising from Lean's errors proves half as many as a fresh attempt (Goedel 11 vs 22 of 107). Geometry: AlphaGeometry's DD+AR engine alone proves 12 of IMO-AG-30 and 187 of JGEX-AG-231; LLM auxiliary points add 13 JGEX problems and only IMO 2014 P4 (d = midpoint of b c).");
}
slideProof("Findings", "Finding 7: proofs need a specialized model, not a fact");

pres.addSection({ title: "Method" });
// 4. Recipe
function slideRecipe(section, title, refs, notes) {   // refs: point each step to its finding slide
const R = (t, r) => refs ? `${t} (${r})` : t;
s = pres.addSlide({ masterName: "Title Only", sectionTitle: section });
s.addText(title, { placeholder: "title" });
function step(s, n, head, res, x, y, w) {
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w, h: 1.35, rectRadius: 0.08, fill: { color: "DEEBF7" }, line: { color: "BDD7EE", width: 0.75 }, objectName: "step " + n });
  s.addShape(pres.shapes.OVAL, { x: x + 0.15, y: y + 0.3, w: 0.7, h: 0.7, fill: { color: BLUE }, line: { color: BLUE }, objectName: "badge " + n });
  s.addText(String(n), { isTextBox: true, x: x + 0.15, y: y + 0.3, w: 0.7, h: 0.7, fontSize: 24, bold: true, color: "FFFFFF", align: "center", valign: "middle", margin: 0 });
  txt(s, head, x + 0.95, y + 0.1, w - 1.05, 1.15, { fontSize: 18, bold: true });
  txt(s, res, x, y + 1.42, w, 0.75, { fontSize: 14, color: C.text2, align: "center", valign: "top" });
}
step(s, 1, "Write a program", R("right on 8 of 8 copies", "slide 2"), 0.6, 1.7, 2.9);
arrow(s, 3.5, 2.37, 3.9, 2.37);
step(s, 2, "Add the missing fact", R("23% → 77–90%; can be automatic", "findings 1, 2, 6"), 3.9, 1.7, 3.0);
arrow(s, 6.9, 2.37, 7.3, 2.37);
step(s, 3, "Run a free check", R("examples, or two versions agree", "finding 3"), 7.3, 1.7, 2.9);
arrow(s, 10.2, 2.1, 10.6, 1.85); arrow(s, 10.2, 2.65, 10.6, 2.95);
box(s, "pass → done", 10.6, 1.55, 2.1, 0.6, "E2F0D9", { fontSize: 16, bold: true });
box(s, "fail → 4. think harder", 10.6, 2.65, 2.1, 0.75, "FADBD8", { fontSize: 16, bold: true });
txt(s, R("same 66%, 18% fewer tokens", "finding 4"), 10.4, 3.45, 2.5, 0.6, { fontSize: 14, color: C.text2, align: "center", valign: "top" });
step(s, 5, "Same problem again? Reuse the checked program", R("valid plans 7% → 94%", "finding 5"), 3.9, 4.3, 6.3);
caption(s, "Together: 87% solved at 2.5k tokens, vs 74% at 4.1k for \"think longer on hard problems\"");
s.addNotes(notes);
}
slideRecipe("Method", "Our method: a recipe built from the findings", true, "Each step is a measured result, shown on the finding slides with an example. Step 1: the polygon. Step 2: delivery routing with OR-Tools (Qwen3-32B). Step 3: free checks (the problem's examples; two versions that should agree). Step 4: contest geometry with gpt-oss-120b. Step 5: reuse on the Solomon routing benchmark. Together (3 models, 624 geometry and optimization problems, 3 seeds): fact first and thinking only on a failed check solves 87% at 2.5k tokens per problem.");

// 4c. The method on one real problem: each step with what it produced, its tokens, and the overall result
function slideMethod(section, title, pre) {
s = pres.addSlide({ masterName: "Title Only", sectionTitle: section });
s.addText(title, { placeholder: "title" });
txt(s, "One real problem (Qwen3-8B): products X, Y, Z cost $10, $15, $20 under three limits. Minimum cost? → 20000", 0.6, 1.28, 12.1, 0.4, { fontSize: 16 });
const STEPS = [["Write a program", "Objective().Minimize()", "✗ crash: no such method", RED, "FADBD8", "without a fact"],
               ["Add the fact", "solver.Minimize(v)", "the call, from its own checked program → prints 20000 ✓", "38761D", "E2F0D9", "316 tokens"],
               ["Free check", "20000 = 20000", "a 2nd version agrees ✓", "38761D", "E2F0D9", "+312 tokens"],
               ["Think harder?", "skipped", "only if the versions differ or crash", "7F7F7F", "F2F2F2", "0 tokens"],
               ["Reuse", "same program", "same kind of problem, new data", BLUE, "DEEBF7", "≈ 0 tokens"]];
STEPS.forEach(([head, big, small, col, fill, cost], k) => {
  const x = 0.6 + k * 2.45;
  s.addShape(pres.shapes.OVAL, { x, y: 1.83, w: 0.5, h: 0.5, fill: { color: BLUE }, line: { color: BLUE }, objectName: "method badge " + (k + 1) });
  s.addText(String(k + 1), { isTextBox: true, x, y: 1.83, w: 0.5, h: 0.5, fontSize: 18, bold: true, color: "FFFFFF", align: "center", valign: "middle", margin: 0 });
  txt(s, head, x + 0.6, 1.83, 1.75, 0.5, { fontSize: 17, bold: true });
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y: 2.45, w: 2.3, h: 1.3, rectRadius: 0.08, fill: { color: fill }, line: { color: col, width: 1 }, objectName: "method step " + head });
  txt(s, big, x + 0.1, 2.5, 2.1, 0.5, { fontSize: big.length > 18 ? 10.5 : big.length > 14 ? 13 : 18, bold: true, color: col, align: "center", fontFace: k < 2 ? "Courier New" : THEME.bodyFontFace });
  txt(s, small, x + 0.1, 3.02, 2.1, 0.68, { fontSize: 13, color: C.text1, align: "center", valign: "top" });
  txt(s, cost, x, 3.8, 2.3, 0.3, { fontSize: 14, bold: true, color: C.text2, align: "center" });
  if (k < 4) arrow(s, x + 2.3, 3.07, x + 2.45, 3.07);
});
function pair(x, head, rows) {   // two labelled bars
  txt(s, head, x, 4.25, 5.9, 0.4, { fontSize: 15, bold: true });
  rows.forEach(([lab, v, shown, col], r) => {
    const y = 4.72 + r * 0.48;
    txt(s, lab, x, y, 2.3, 0.4, { fontSize: 14, align: "right" });
    s.addShape(pres.shapes.RECTANGLE, { x: x + 2.4, y: y + 0.08, w: Math.max(0.05, 2.4 * v), h: 0.26, fill: { color: col }, line: { color: col, width: 0.5 }, objectName: head + " " + lab });
    txt(s, shown, x + 2.5 + 2.4 * v, y, 1.3, 0.4, { fontSize: 14, bold: true, color: col });
  });
}
pair(0.6, "This problem: tokens (both answers right)", [["always think", 1.0, "5.3k", "7F7F7F"], ["our method", 0.12, "0.6k", BLUE]]);
pair(6.8, "All 624 problems, 3 models: % solved · tokens", [["think on hardest", 0.74, "74% · 4.1k", "7F7F7F"], ["our method", 0.87, "87% · 2.5k", BLUE]]);
txt(s, "Free check, no answers needed:", 0.6, 5.85, 3.1, 0.45, { fontSize: 14, bold: true });
[["contest", "sample tests pass"], ["geometry", "moved copies agree"], ["routing", "plan obeys rules"], ["word problems", "two versions agree"]].forEach(([k, v], r) => {
  box(s, "", 3.7 + r * 2.27, 5.83, 2.17, 0.5, "F2F2F2");
  txt(s, [{ text: k + ": ", options: { bold: true } }, { text: v }], 3.75 + r * 2.27, 5.83, 2.07, 0.5, { fontSize: 13, align: "center" });
});
s.addNotes((pre || "") + "Real run (Qwen3-8B, MAMO easy-189, answer 20000). 1: without a fact the program calls Objective().Minimize(), which does not exist, and crashes. 2: the fact is the model's own earlier program for another problem (vans and trucks) that passed the check; with it the program writes solver.Minimize(10*x + 15*y + 20*z) and prints 20000 (316 tokens). 3: the free check, a second version, also prints 20000 (312 tokens): they agree. 4: so no thinking (thinking alone took 5,323 tokens). 5: the same kind of problem with new data reuses the checked program. Bottom: this problem 0.6k vs 5.3k tokens; over 624 geometry and optimization problems (Qwen3-8B, Qwen3-32B, Qwen3.6, 3 seeds) 87% at 2.5k vs 74% at 4.1k for thinking on the hardest-looking problems. The free check in each domain needs no answers: contest sample tests, geometry copies that must agree, routing plans that must obey every rule, word problems with two versions that must agree.");
}
slideMethod("Method", "Our method on one real problem");

// 9. All together
function slideTogether(section, title, pre) {   // pre: text put before the speaker notes
s = pres.addSlide({ masterName: "Title Only", sectionTitle: section });
s.addText(title, { placeholder: "title" });
txt(s, "Same 624 geometry and optimization problems, 3 models: % solved · tokens per problem", 0.6, 1.35, 12.1, 0.45, { fontSize: 18 });
hbars(s, 0.6, 1.95, 8.2, [["First program, no help", 63, "63% · 0.7k", "A5A5A5"],
                          ["Think on hardest-looking", 74, "74% · 4.1k", "7F7F7F"],
                          ["Think when check fails", 77, "77% · 4.2k", "7F7F7F"],
                          ["Fix by failure type", 83, "83% · 4.2k", THEME.colors.accent2],
                          ["Retrieved fact, then think", 84, "84% · 3.3k", "5B9BD5"],
                          ["Fact first, then think", 87, "87% · 2.5k", BLUE]], 0.62, 2.9, 1.7);
panel(s, 9.0, 1.9, 3.7, 3.9, "new task");
txt(s, "A new task? Label 30 problems", 9.2, 2.0, 3.3, 0.75, { fontSize: 17, bold: true, valign: "top" });
txt(s, "points lost vs the best policy, over 63 settings (lower is better)", 9.2, 2.75, 3.3, 0.6, { fontSize: 13, color: C.text2, valign: "top" });
[["always think", 8.4, "A5A5A5"], ["fact first (default)", 1.4, BLUE], ["pick on 30 labels", 0.6, BLUE]].forEach(([lab, v, col], r) => {
  const y = 3.5 + r * 0.7;
  txt(s, lab, 9.2, y, 3.3, 0.3, { fontSize: 14 });
  s.addShape(pres.shapes.RECTANGLE, { x: 9.2, y: y + 0.32, w: Math.max(0.05, 0.3 * v), h: 0.22, fill: { color: col }, line: { color: col, width: 0.5 }, objectName: "loss " + lab });
  txt(s, String(v), 9.3 + 0.3 * v, y + 0.25, 0.6, 0.35, { fontSize: 14, bold: true, color: col === "A5A5A5" ? "595959" : col });
});
caption(s, "Most accurate and among the cheapest on all 3 seeds: spend thinking where a check fails");
s.addNotes((pre || "") + "Right panel (MODEL, 63 model x task x seed cells; 0.5 points per 1k tokens): fact first, think on failure is the best fixed default (1.4 points from each cell's best policy; always thinking 8.4); choosing among 4 policies on 30 labelled problems of the new task cuts it to 0.6 (MAMO: 0.8-1.4). U1 / U1r / U2 (pre-registered). Qwen3-8B, Qwen3-32B and Qwen3.6 on the generated geometry and optimization suites, 624 problems, cure seed 1 shown; the order is the same on seeds 2 and 3. Thinking on the hardest-looking problems (difficulty-based allocation, as in compute-optimal scaling work) is even below thinking whenever the check fails. Giving the fact first and thinking only when the check fails is the most accurate and uses fewer tokens than any thinking policy; with automatically retrieved facts (BM25) it still reaches 84%.");
}
slideTogether("Method", "All together: facts first, think only on failure");

// 9b. Published methods
function slideBaselines(section, title, pre) {   // pre: text put before the speaker notes
s = pres.addSlide({ masterName: "Title Only", sectionTitle: section });
s.addText(title, { placeholder: "title" });
{
  const OURS = (t) => ({ text: t, options: { bold: true, color: "38761D" } });
  const rows = [
    [HDR("Task"), HDR("Published method"), HDR("Its result"), HDR("Ours (same problems)")],
    ["Where to spend thinking", "think on the hardest-looking problems (Snell et al. 2025)", "74% · 4.1k", OURS("fact first, think on failure: 87% · 2.5k")],
    ["Contest geometry", "always high effort (reasoning-model default)", "66.2% · 30.1k", OURS("think only on a failed check: 66.3% · 24.7k")],
    ["Pick 1 of 3 programs", "CodeT: the model writes tests", "96.0% (+340 tokens)", OURS("symmetry check: 99.7% (0 tokens)")],
    ["Library documentation", "DRoC: decompose, retrieve per constraint (ICLR 2025)", "72% · 2.1k", OURS("exact 5-line snippet: 77% · 1.7k")],
    ["Unneeded tools", "System 2 Attention / a \"use only if needed\" sentence", "64% / 76%", OURS("only the needed tools: 92%")],
    ["Daily routing", "Dynamic Cheatsheet: the model's own notes", "31–40%", OURS("reuse a checked program: 94%")],
    ["Word problems (held-out MAMO)", "ORLM-8B: a fine-tuned modeling specialist", "69.5% · 1.1k", OURS("Qwen3-8B, no training: 69.5% · 1.0k; gpt-oss-20b 78.8%")],
  ];
  table(s, rows, { x: 0.6, y: 1.45, w: 12.1, colW: [2.3, 3.9, 2.2, 3.7], rowH: 0.57, fontSize: 15 });
}
caption(s, "Measured here with the same problems and models: the recipe is more accurate, cheaper, or both");
s.addNotes((pre || "") + "All baselines were run by us on our benchmarks. Models: U1 policies over Qwen3-8B / Qwen3-32B / Qwen3.6 (624 problems); contest geometry gpt-oss-120b (311); selection Qwen3-8B (300 geometry instances, 3 candidates); documentation Qwen3-32B on CVRP; tools Qwen3-32B on 5 geometry tasks; daily routing gpt-oss-120b on 48 held-out Solomon instances. Tokens are output tokens per problem. ORLM-LLaMA-3-8B was run in our harness on MAMO (863 held-out word problems; greedy 80.5 / 35.5% on Easy / Complex, as reported). More rows (MBR-exec, majority vote, DeepConf, Self-Debugging, Mixture-of-Thought cascade, BM25 retrieval) are in PROPOSAL.md section 6.");
}
slideBaselines("Method", "Compared with published methods");

// 9c. Related research: where this work sits, and numbers reported in papers
function slideRelated(section, title, pre) {
s = pres.addSlide({ masterName: "Title Only", sectionTitle: section });
s.addText(title, { placeholder: "title" });
const ADD = (t) => ({ text: t, options: { color: "38761D" } });
table(s, [
  [HDR("Theme"), HDR("Closest work"), HDR("What we add")],
  ["Programs instead of text", "PAL, Program-of-Thoughts, Mixture-of-Thought (ICLR 2024)", ADD("when a program helps; text vs program as a free check")],
  ["Library facts for code", "DRoC (ICLR 2025), CP-Bench, CloudAPIBench, DRAFT", ADD("5 exact lines beat the manual and thinking; facts mined without a human")],
  ["Misleading context", "Invisible Lottery (2606.04057), unneeded tools (2609.14157), CodeCrash, S2A", ADD("the harm on exact geometry, turned into a check")],
  ["Choosing a program", "CodeT, MBR-exec, AlphaCode's example filter, DeepConf", ADD("symmetry check of one program: 99.7% vs CodeT 96.0%")],
  ["Spending test-time compute", "Snell et al. 2025, FrugalGPT, DART, Thinkless, AdaptThink", ADD("fact + execution check, no training: 87% vs 74%")],
  ["Optimization modeling", "ORLM, STORM, EVOM, OR-R1 (trained); OptiMUS, OptiSkill (agents)", ADD("training-free, no answers; matches fine-tuned ORLM-8B")],
  ["One program, many instances", "FunSearch, HeuriGym, ARS, 2605.14141", ADD("measured 7% → 94%; edit a verified program for new rules")],
  ["Proofs", "Goedel-Prover-V2, DeepSeek-Prover-V2, AlphaGeometry", ADD("facts and checks do not carry over: use a specialized prover")],
], { x: 0.6, y: 1.35, w: 12.1, colW: [2.6, 4.9, 4.6], rowH: 0.57, fontSize: 13 });
s.addNotes((pre || "") + "Closest work per theme (details and how we differ: PROPOSAL.md section 6.1 and docs/notes/RELATED_WORK.md). Closest overall: OptiSkill (2609.22987) builds a skill bank from a strong teacher's programs validated against answers and routes it by problem type; our facts are the same small model's own programs chosen by a label-free check, and we show why routing by problem type is needed (a fact from another type costs 14-21 points). For when-to-think, Thinkless and AdaptThink train a switch with RL; we decide with an execution check after giving the fact; a same-backbone comparison with AdaptThink-7B is running.");
}
slideRelated("Method", "Where this work sits in related research");

function slideReported(section, title, pre) {
s = pres.addSlide({ masterName: "Title Only", sectionTitle: section });
s.addText(title, { placeholder: "title" });
const OURS = (t) => ({ text: t, options: { bold: true, color: "38761D" } });
table(s, [
  [HDR("Benchmark"), HDR("Reported in the paper or model card"), HDR("Ours")],
  ["MAMO Easy / Complex", "ORLM-LLaMA-3-8B 82.3 / 37.4% (fine-tuned)\nSTORM-Qwen3-4B 86.3 / 70.3% (SFT + RL)\nOptiSkill with frontier models 90.8–94.3 / 56.8–64.0%",
   OURS("no training: Qwen3-14B 82.8 / 37.4%, gpt-oss-20b 85.6 / 57.8%\nORLM-8B in our harness: 80.5 / 35.5%")],
  ["miniF2F, 32 tries", "Goedel-Prover-V2-8B 84.6%", OURS("the same model in our harness: 76.6%")],
  ["IMO-AG-30 geometry", "AlphaGeometry 25 of 30; its symbolic engine alone 14; average IMO gold medallist 25.9, average participant 15.2", OURS("engine alone 12 in our setup; with our models' points 13")],
], { x: 0.6, y: 1.5, w: 12.1, colW: [2.4, 5.0, 4.7], rowH: [0.5, 1.3, 0.6, 0.9], fontSize: 15 });
caption(s, "Different harnesses and graders: for orientation only");
s.addNotes((pre || "") + "Numbers as reported by the papers or model cards; our harness, prompts and graders differ (MAMO labels are noisy; reported ORLM numbers range 81.6-88.2% on Easy). ORLM-8B rerun in our harness gives 80.5 / 35.5%, close to its report. STORM-Qwen3-4B is being run in our harness. Goedel-Prover-V2-8B: 187 of 244 with 32 tries in our Lean setup vs 84.6% on its card. AlphaGeometry's DD+AR engine proves 12 of IMO-AG-30 here (14 in the paper; one problem does not parse in this engine version).");
}
slideReported("Method", "Numbers reported in papers, next to ours");

// 9d. Setup and fairness (models, benchmarks, scoring, how comparisons are kept fair)
function slideSetup(section, title, pre) {
s = pres.addSlide({ masterName: "Title Only", sectionTitle: section });
s.addText(title, { placeholder: "title" });
[["robot", "Models", "open models run locally: Qwen3 1.7B–32B, Qwen3.6-35B, gpt-oss-20b and 120b; Goedel- and DeepSeek-Prover for proofs"],
 ["shapes", "Benchmarks", "13 geometry and 8 optimization tasks (generated); 311 Codeforces geometry; 56 Solomon routing; 82 job-shop; 1,208 word problems (NL4OPT, IndustryOR, MAMO); MATH-500 + AIME; miniF2F"],
 ["check", "Exact scoring", "geometry right on all 8 moved copies; plans obey every rule; contest programs pass all official tests; math and word problems by exact answer"],
 ["fact", "Fair comparisons", "one change at a time; predictions written before each run; every claim on 3 seeds; baselines run in our own harness"],
 ["coins", "Cost", "every result reported with its output tokens per problem"],
 ["gpu", "Hardware", "one model per GPU (RTX PRO 6000, 96 GB); the small models fit one 24 GB GPU"]].forEach(([icon, head, body], k) => {
  const x = 0.6 + (k % 2) * 6.15, y = 1.4 + Math.floor(k / 2) * 1.75;
  panel(s, x, y, 5.95, 1.6, head);
  s.addImage({ path: ICON(icon), x: x + 0.2, y: y + 0.2, w: 0.5, h: 0.5, objectName: "icon " + icon });
  txt(s, head, x + 0.85, y + 0.15, 4.9, 0.5, { fontSize: 18, bold: true });
  txt(s, body, x + 0.85, y + 0.65, 4.95, 0.9, { fontSize: 14, valign: "top" });
});
s.addNotes((pre || "") + "How we test. Models: open models run locally (Qwen3 1.7B, 4B, 8B, 14B, 32B; Qwen3.6-35B-A3B; gpt-oss-20b and 120b; Goedel-Prover-V2-8B and DeepSeek-Prover-V2-7B for Lean). Benchmarks with exact answers. Every comparison changes one thing, is pre-registered (predictions written before the run, docs/prereg), replicated on 3 seeds, and reports output tokens per problem; published baselines are rerun in the same harness.");
}
slideSetup("Method", "Setup and fairness");

// 10. Limits and next
function slideLimits(section, title, pre) {   // pre: text put before the speaker notes
s = pres.addSlide({ masterName: "Title Only", sectionTitle: section });
s.addText(title, { placeholder: "title" });
[["Where it stops", RED, [
   "Proofs: a skill, not a fact (use a specialized prover)",
   "Automatic facts only within one kind of problem",
   "Checks leak: 24–37% of wrong contest programs pass the examples",
   "Missing world knowledge: thinking adds 2–5 points at 70–200× tokens"]],
 ["Next", BLUE, [
   "Repeat the held-out MAMO test for 3 more models (3 seeds)",
   "Automatic facts for each problem type",
   "Final report; a commercial model if available"]]].forEach(([head, col, items], i) => {
  const x = 0.6 + i * 6.15;
  panel(s, x, 1.55, 5.95, 4.1, head);
  txt(s, head, x + 0.3, 1.7, 5.35, 0.6, { fontSize: 26, bold: true, color: col });
  bullets(s, items, { x: x + 0.3, y: 2.4, w: 5.35, h: 3.1, fontSize: 17 });
});
caption(s, "Every claim pre-registered and checked on 3 seeds; accuracy always reported with its token cost");
s.addNotes((pre || "") + "Updated 2026-10-19. Done since the last version: contest geometry and competition math on 24 GB GPUs, Qwen3.6 with the model card settings (headline unchanged), automatic facts and the held-out MAMO test, the policy model, proofs. Older notes: for Lean proofs an invented lemma stands for a missing proof step (similar-name feedback fixes 2.7%, a fresh try 3.2%); for PopQA thinking adds 1.8-5 points at 70-200 times the tokens, only for well-known facts. Checks leak, which caps every policy. Facts were hand-written; BM25 retrieval recovers most of the gain. Next: SIZE-CC (gpt-oss-20b on contest geometry with check-gated escalation), X1-SIZE (competition math for Qwen3-4B/8B/14B), automatic facts, a closed API model, final report.");
}
pres.addSection({ title: "Next" });
slideLimits("Next", "Where the recipe stops, and what is next");

const FULL = path.join(ROOT, "PROPOSAL_slides_full.pptx");
pres.writeFile({ fileName: FULL }).then(async () => { await applyTheme(FULL, THEME); console.log("written", FULL); buildTalk(); });

// ================= 5-minute talk + 5 minutes of questions (PROPOSAL_slides.pptx): 8 slides, then extra pages =================
function buildTalk() {
  pres = newDeck();
  pres.addSection({ title: "Talk" });
  slideTitle("Talk", "POSTECH CSED490E (Graduate NLP) · Team 5 · 5-minute proposal talk",
    "(5 s) Hello, we are Team 5. Our project: how to solve computational math with LLMs accurately and cheaply. The question is where the extra effort should go: a fact, a check, or more thinking.");

  // 2. the problem: programs beat words, but they fail silently and thinking is expensive
  s = pres.addSlide({ masterName: "Title Only", sectionTitle: "Talk" });
  s.addText("Programs help, but two things go wrong", { placeholder: "title" });
  [["pen", "answer in words"], ["code", "write a program"], ["gears", "call a solver library"], ["brain", "think longer first"]].forEach(([icon, t], k) => {
    const x = 0.6 + k * 3.05;
    box(s, "", x, 1.3, 2.9, 0.6, "F2F2F2");
    s.addImage({ path: ICON(icon), x: x + 0.15, y: 1.37, w: 0.46, h: 0.46, objectName: "icon " + icon });
    txt(s, t, x + 0.75, 1.3, 2.1, 0.6, { fontSize: 16, bold: true });
  });
  function pane2(x, head, col, fill) {
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y: 2.1, w: 3.95, h: 3.05, rectRadius: 0.08, fill: { color: fill }, line: { color: col, width: 1 }, objectName: "pane " + head });
    txt(s, head, x + 0.2, 2.17, 3.6, 0.45, { fontSize: 18, bold: true, color: col });
  }
  pane2(0.6, "Programs beat words", BLUE, "EEF3FB");
  s.addImage({ path: FIG("slide2_shapes.png"), x: 0.8, y: 2.68, w: 3.55, h: 0.77, objectName: "four copies of one polygon", altText: "one polygon: original, moved, turned, flipped" });
  [["words", [["436", 1], ["2944", 0], ["392", 0], ["728", 0]], 3.6], ["program", [["436", 1], ["436", 1], ["436", 1], ["436", 1]], 4.15]].forEach(([lab, ans, y]) => {
    txt(s, lab, 0.75, y, 0.85, 0.42, { fontSize: 14, bold: true });
    ans.forEach(([t, ok], k) => {
      const x = 1.6 + k * 0.72;
      s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w: 0.66, h: 0.42, rectRadius: 0.08, fill: { color: ok ? "E2F0D9" : "FADBD8" }, line: { color: ok ? GREEN : RED, width: 0.75 }, objectName: `${lab} ${k}` });
      txt(s, t, x, y, 0.66, 0.42, { fontSize: 14, bold: true, align: "center", color: ok ? "38761D" : RED });
    });
  });
  txt(s, "the same shape, moved and turned (Qwen3-8B)", 0.75, 4.62, 3.7, 0.4, { fontSize: 14, color: C.text2 });
  pane2(4.7, "1. They fail silently", RED, "FDF2F1");
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 4.85, y: 2.7, w: 3.65, h: 1.2, rectRadius: 0.05, fill: { color: "262626" }, line: { color: "262626" }, objectName: "terminal" });
  s.addText([{ text: "task only     → 6", options: { color: "8FD16A", bold: true, breakLine: true } },
             { text: "+ 8 helpers   → 0", options: { color: "FF7B7B", bold: true, breakLine: true } },
             { text: "(no error message)", options: { color: "BFBFBF" } }],
    { isTextBox: true, x: 5.0, y: 2.72, w: 3.4, h: 1.16, fontFace: "Courier New", fontSize: 15, valign: "middle", margin: 0 });
  txt(s, [{ text: "24–37%", options: { bold: true, fontSize: 22, color: RED } }, { text: " of wrong programs pass the problem's own examples" }],
      4.9, 4.0, 3.6, 1.05, { fontSize: 14, valign: "top" });
  pane2(8.8, "2. Thinking is expensive", THEME.colors.accent2, "FDF0E6");
  [["medium", "57%", 10, "page", 2.75], ["high", "66%", 43, "pagehot", 3.25]].forEach(([lab, acc, n, icon, y]) => {
    txt(s, [{ text: lab + " ", options: { bold: true } }, { text: acc }], 8.95, y, 1.15, 0.4, { fontSize: 14 });
    for (let k = 0; k < n; k++) s.addImage({ path: ICON(icon), x: 10.1 + (k % 15) * 0.17, y: y + 0.03 + Math.floor(k / 15) * 0.2, w: 0.16, h: 0.18, objectName: `${lab} page ${k}` });
  });
  txt(s, "one page ≈ 700 tokens", 8.95, 3.95, 3.6, 0.3, { fontSize: 14, color: C.text2 });
  txt(s, [{ text: "4.4× tokens", options: { bold: true, fontSize: 22, color: THEME.colors.accent2 } }, { text: " for 9 more points (311 contest problems)" }],
      8.95, 4.3, 3.65, 0.85, { fontSize: 14, valign: "top" });
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 0.6, y: 5.35, w: 12.1, h: 0.8, rectRadius: 0.08, fill: { color: "DEEBF7" }, line: { color: "BDD7EE", width: 0.75 }, objectName: "our question" });
  txt(s, "Where should the extra effort go?", 0.85, 5.35, 4.4, 0.8, { fontSize: 19, bold: true, color: BLUE });
  [["fact", "a missing fact", "E2F0D9", "38761D"], ["check", "a free check", "E2F0D9", "38761D"], ["brain", "more thinking", "FADBD8", RED]].forEach(([icon, t, fill, col], k) => {
    const x = 5.3 + k * 2.45;
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y: 5.48, w: 2.3, h: 0.55, rectRadius: 0.2, fill: { color: fill }, line: { color: col, width: 1 }, objectName: "option " + t });
    s.addImage({ path: ICON(icon), x: x + 0.14, y: 5.57, w: 0.36, h: 0.36, objectName: "icon " + icon });
    txt(s, t, x + 0.62, 5.48, 1.65, 0.55, { fontSize: 16, bold: true, color: col });
  });
  caption(s, "It matters: agents already write such code, tokens cost money, and most teams have one small GPU");
  s.addNotes("(40 s) An LLM can answer a math problem in words, write a program, call a solver library, or think longer first. For computation, programs win: asked for the area of the same shape moved and turned, Qwen3-8B answers 436, 2944, 392, 728 in words, but its program says 436 every time. Two things go wrong. Programs fail silently: the same model's hull program prints 6, or 0 when extra helper functions are in the prompt, with no error; and a quarter to a third of wrong programs pass the problem's own examples. And thinking is expensive: high effort uses 4.4 times the tokens for 9 more points. So: where should the extra effort go?");

  // 3. what we solve, and how hard
  s = pres.addSlide({ masterName: "Title Only", sectionTitle: "Talk" });
  s.addText("What we solve, and how hard it is", { placeholder: "title" });
  [["shapes", "Geometry", "corners of the rubber band around 10 points", "textbook algorithms, exact on every copy", BLUE],
   ["trophy", "Contest problems", "311 Codeforces geometry problems", "Codeforces Master to Grandmaster level", RED],
   ["truck", "Routing, scheduling", "routes for 100 customers with time windows", "classic OR benchmark: greedy is 48% worse", THEME.colors.accent2],
   ["calc", "Word problems", "most coins from 500 gold and 300 wires?", "OR-course exercises (NL4OPT)", "38761D"],
   ["sqrt", "Math and proofs", "AIME answers; Lean proofs", "AIME: top ~5% of AMC; IMO gold: 25.9/30", "595959"]].forEach(([icon, head, ex, tag, col], k) => {
    const x = 0.6 + k * 2.45;
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y: 1.4, w: 2.3, h: 4.45, rectRadius: 0.08, fill: { color: "F7F7F7" }, line: { color: "D9D9D9", width: 0.75 }, objectName: "kind " + head });
    s.addImage({ path: ICON(icon), x: x + 0.75, y: 1.6, w: 0.8, h: 0.8, objectName: "icon " + icon });
    txt(s, head, x + 0.1, 2.55, 2.1, 0.75, { fontSize: 18, bold: true, align: "center" });
    txt(s, ex, x + 0.15, 3.35, 2.0, 1.2, { fontSize: 15, align: "center", valign: "top" });
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: x + 0.1, y: 4.7, w: 2.1, h: 0.95, rectRadius: 0.1, fill: { color: "FFFFFF" }, line: { color: col, width: 1.25 }, objectName: "tag " + head });
    txt(s, tag, x + 0.15, 4.7, 2.0, 0.95, { fontSize: 15, bold: true, color: col, align: "center" });
  });
  caption(s, "Contest problems: median = Codeforces Master; 46% are at Grandmaster level");
  s.addNotes("(25 s) We test five kinds of computational math, and here is how hard they are by well-known yardsticks. Exact geometry uses textbook algorithms, but must be right on moved and turned copies. Our contest problems are Codeforces problems at the level of Master to Grandmaster players; 18% are solved by none of our nine model setups. Routing is a classic operations-research benchmark where a simple greedy plan is 48% worse than the best known. Word problems are operations-research course exercises. And competition math goes up to AIME, taken by the top few percent of AMC students, and olympiad proofs, where an IMO gold medallist solves about 26 of 30 geometry problems.");

  // 4. finding 1
  s = pres.addSlide({ masterName: "Title Only", sectionTitle: "Talk" });
  s.addText("Finding 1: give the fact, not the manual", { placeholder: "title" });
  txt(s, "Qwen3-32B plans delivery routes with Google's OR-Tools library", 0.6, 1.3, 12.1, 0.45, { fontSize: 17 });
  [["with the whole manual", "RegisterUnaryLongLivingCallback()", "✗ does not exist: crash", "FCE4D6", RED, 1.95],
   ["with 5 exact lines", "RegisterUnaryTransitCallback()", "✓ runs: best route", "E2F0D9", "38761D", 2.75]].forEach(([lab, call, res, fill, col, y]) => {
    box(s, lab, 0.6, y, 2.7, 0.6, fill, { fontSize: 16, bold: true });
    arrow(s, 3.3, y + 0.3, 3.65, y + 0.3);
    code(s, call, 3.65, y, 4.9, 0.6, col, 15);
    txt(s, res, 8.75, y, 3.9, 0.6, { fontSize: 17, bold: true, color: col });
  });
  txt(s, "Routing problems solved optimally (out of 100):", 0.6, 3.65, 12.1, 0.4, { fontSize: 17, bold: true });
  hbars(s, 0.6, 4.1, 12.1, [["nothing extra", 23, "23", "7F7F7F"], ["think longer", 3, "3", RED], ["whole manual", 7, "7", RED], ["5 exact lines", 83, "77–90", BLUE]], 0.5, 2.6);
  caption(s, "Thinking cannot supply a fact the model does not have");
  s.addNotes("(35 s) Finding one. Qwen3-32B writes route-planning code with OR-Tools. Given the whole manual, it calls a function that sounds right but does not exist, and the program crashes. Given five lines with the exact call, it finds the best route. Out of 100 routing problems: 23 with nothing extra, only 3 when it thinks longer, 7 with the whole manual, and 77 to 90 with five exact lines. Thinking cannot supply a fact the model does not have.");

  // 5. finding 2: free checks decide when to think
  s = pres.addSlide({ masterName: "Title Only", sectionTitle: "Talk" });
  s.addText("Finding 2: think harder only when a free check fails", { placeholder: "title" });
  function checkPane(x, head, rows, bars, sub) {
    panel(s, x, 1.35, 5.95, 4.6, head);
    txt(s, head, x + 0.25, 1.45, 5.45, 0.5, { fontSize: 18, bold: true, color: BLUE });
    rows.forEach(([t, col, fill], r) => box(s, t, x + 0.25, 2.05 + r * 0.72, 5.45, 0.6, fill, { fontSize: 15, color: col }));
    txt(s, sub, x + 0.25, 3.6, 5.45, 0.4, { fontSize: 14, color: C.text2 });
    bars.forEach(([lab, v, shown, col], r) => {
      const y = 4.05 + r * 0.6;
      txt(s, lab, x + 0.25, y, 2.2, 0.5, { fontSize: 14, align: "right" });
      s.addShape(pres.shapes.RECTANGLE, { x: x + 2.55, y: y + 0.12, w: 1.6 * v, h: 0.28, fill: { color: col }, line: { color: col, width: 0.5 }, objectName: head + " " + lab });
      txt(s, shown, x + 2.65 + 1.6 * v, y, 1.6, 0.5, { fontSize: 15, bold: true, color: col });
    });
  }
  checkPane(0.6, "Check A: the problem's own examples", [["\"Make a triangle!\": examples pass → submit", "38761D", "E2F0D9"], ["\"Arrow\": an example fails → think harder → right", RED, "FADBD8"]],
            [["always think hard", 1.0, "66.2% · 30k", "7F7F7F"], ["only on failure", 0.82, "66.3% · 25k", BLUE]], "311 contest problems (gpt-oss-120b), tokens per problem:");
  checkPane(6.75, "Check B: two versions must agree", [["task only → program prints 6", "38761D", "E2F0D9"], ["+ 8 unneeded helpers → prints 0 → differ → think", RED, "FADBD8"]],
            [["always think", 1.0, "98% · 5.9k", "7F7F7F"], ["only if they differ", 0.73, "99% · 4.3k", BLUE]], "108 geometry problems (Qwen3-32B, 3 runs):");
  caption(s, "Same accuracy as always thinking, with 18–27% fewer tokens; no answers needed");
  s.addNotes("(40 s) Finding two: thinking should be paid only when a free check fails. Check A uses the examples printed in every contest problem: 'Make a triangle!' passes them and is submitted; 'Arrow' fails one, so only it gets high effort. Same 66% as always thinking hard, 18% fewer tokens. Check B writes the program twice, with and without extra tools: if the answers differ, think. 99% vs 98%, with 27% fewer tokens. Neither check needs the answer.");

  // 6. the method on one problem, and what it gives overall
  s = pres.addSlide({ masterName: "Title Only", sectionTitle: "Talk" });
  s.addText("Our method: cheap steps first", { placeholder: "title" });
  txt(s, "One real problem (Qwen3-8B): products X, Y, Z at $10, $15, $20 under three limits; minimum cost? → 20000", 0.6, 1.28, 12.1, 0.4, { fontSize: 16 });
  [["1 Program", "Objective()\n.Minimize()", "✗ crash, no fact", RED, "FADBD8", 1.0],
   ["2 + Fact", "solver\n.Minimize(...)", "found automatically: its own checked program", "38761D", "E2F0D9", 1.0],
   ["3 Free check", "20000 = 20000", "a second version agrees", "38761D", "E2F0D9", 1.0],
   ["4 Think?", "skipped", "only if they differ", "7F7F7F", "F2F2F2", 1.0],
   ["5 Reuse", "same program", "same kind, new data", BLUE, "DEEBF7", 1.0]].forEach(([head, big, small, col, fill], k) => {
    const x = 0.6 + k * 2.45;
    txt(s, head, x, 1.78, 2.3, 0.4, { fontSize: 17, bold: true, color: BLUE });
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y: 2.2, w: 2.3, h: 1.45, rectRadius: 0.08, fill: { color: fill }, line: { color: col, width: 1 }, objectName: "step " + head });
    txt(s, big, x + 0.08, 2.25, 2.14, 0.62, { fontSize: k < 2 ? 14 : 18, bold: true, color: col, align: "center", fontFace: k < 2 ? "Courier New" : THEME.bodyFontFace });
    txt(s, small, x + 0.1, 2.9, 2.1, 0.72, { fontSize: 14, align: "center", valign: "top" });
    if (k < 4) arrow(s, x + 2.3, 2.92, x + 2.45, 2.92);
  });
  txt(s, "All 624 geometry and optimization problems, 3 models:", 0.6, 3.95, 7.0, 0.4, { fontSize: 16, bold: true });
  hbars(s, 0.6, 4.4, 7.2, [["think on hardest", 74, "74% · 4.1k", "7F7F7F"], ["our method", 87, "87% · 2.5k", BLUE]], 0.6, 2.2, 1.6);
  [["79% = 79%", "automatic fact vs hand-written, on a benchmark never used before"], ["0.6k vs 5.3k", "tokens on this problem vs thinking alone"]].forEach(([big, lab], r) => {
    const y = 3.95 + r * 1.05;
    txt(s, big, 8.2, y, 4.5, 0.5, { fontSize: 24, bold: true, color: BLUE });
    txt(s, lab, 8.2, y + 0.48, 4.5, 0.5, { fontSize: 14, valign: "top" });
  });
  caption(s, "More accurate and cheaper than spending thinking on the hardest-looking problems");
  s.addNotes("(60 s) Together this gives our method, shown on one real word problem. Without a fact, the program calls a method that does not exist. The fact is found automatically: the model's own earlier program for another problem that passed the check, showing the right call. With it, two versions both print 20000, they agree, so we skip thinking and accept: 0.6 thousand tokens instead of 5.3 thousand. A problem of the same kind with new data reuses the checked program. Over 624 problems and 3 models: 87% at 2.5 thousand tokens, versus 74% at 4.1 thousand for the usual idea of thinking more on the hardest-looking problems. And the automatic fact matches a hand-written one on a benchmark we never used before: 79 versus 79%.");

  // 7. what is new (the usual way vs ours, row by row), what is next (a timeline), and the takeaway
  s = pres.addSlide({ masterName: "Title Only", sectionTitle: "Talk" });
  s.addText("What is new, and what is next", { placeholder: "title" });
  txt(s, "The usual way", 0.6, 1.3, 5.3, 0.4, { fontSize: 16, bold: true, color: "7F7F7F", align: "center" });
  txt(s, "Ours", 7.4, 1.3, 5.3, 0.4, { fontSize: 16, bold: true, color: BLUE, align: "center" });
  [["brain", "think more on hard-looking problems, or train when to think", "check", "think only when a free check fails; no training (87% vs 74%)"],
   ["page", "give the manual, or a teacher's programs checked against answers", "fact", "give one fact: the model's own checked program; no answers"],
   ["robot", "fine-tune a specialist model (ORLM-8B)", "gpu", "no training, one 24 GB GPU: the same 69.5%"]].forEach(([li, lt, ri, rt], r) => {
    const y = 1.75 + r * 0.9;
    box(s, "", 0.6, y, 5.3, 0.75, "F2F2F2");
    s.addImage({ path: ICON(li), x: 0.75, y: y + 0.15, w: 0.45, h: 0.45, objectName: "usual icon " + r });
    txt(s, lt, 1.35, y, 4.45, 0.75, { fontSize: 15, color: "404040" });
    s.addShape(pres.shapes.RIGHT_ARROW, { x: 6.1, y: y + 0.17, w: 1.1, h: 0.42, fill: { color: BLUE }, line: { color: BLUE }, objectName: "arrow " + r });
    box(s, "", 7.4, y, 5.3, 0.75, "DEEBF7");
    s.addImage({ path: ICON(ri), x: 7.55, y: y + 0.15, w: 0.45, h: 0.45, objectName: "ours icon " + r });
    txt(s, rt, 8.15, y, 4.45, 0.75, { fontSize: 15, bold: true, color: "1F3864" });
  });
  // next steps as a timeline
  txt(s, "Next, until the final report", 0.6, 4.5, 12.1, 0.4, { fontSize: 16, bold: true });
  s.addShape(pres.shapes.LINE, { x: 2.4, y: 5.25, w: 8.5, h: 0, line: { color: "BFBFBF", width: 3 } });
  [["check", "replicate on held-out data; run the closest baselines"], ["fact", "find facts for every problem type"], ["code", "final report, code, and the recipe as a tool"]].forEach(([icon, t], k) => {
    const x = 2.4 + k * 4.25;
    s.addShape(pres.shapes.OVAL, { x: x - 0.3, y: 4.95, w: 0.6, h: 0.6, fill: { color: "FFFFFF" }, line: { color: BLUE, width: 2 }, objectName: "milestone " + k });
    s.addImage({ path: ICON(icon), x: x - 0.19, y: 5.06, w: 0.38, h: 0.38, objectName: "milestone icon " + k });
    txt(s, t, x - 1.8, 5.58, 3.6, 0.55, { fontSize: 15, align: "center", valign: "top" });
  });
  caption(s, "Takeaway: give the missing fact first, and think only where a free check fails");
  s.addNotes("(30 s) What is new, compared with the usual way. Usually more compute goes to hard-looking problems, or a model is trained to decide when to think; we think only when a free check fails, with no training: 87 versus 74%. Usually models get the manual, or a teacher's programs checked against answers; we give one fact, the model's own checked program, with no answers. And instead of fine-tuning a specialist, an untrained 8B model on one GPU gets the same 69.5%. Next: replicate on held-out data and run the closest baselines, find facts for every problem type, and release the report, code and recipe. Takeaway: give the missing fact first, and think only where a free check fails. Thank you.");

  function slidePays(section, title) {
  s = pres.addSlide({ masterName: "Title Only", sectionTitle: section });
  s.addText(title, { placeholder: "title" });
  txt(s, "624 geometry and optimization problems, 3 models: % solved · tokens per problem", 0.6, 1.35, 7.6, 0.45, { fontSize: 16 });
  hbars(s, 0.6, 1.95, 7.6, [["Think on hardest (Snell et al.)", 74, "74% · 4.1k", "7F7F7F"],
                            ["Think when the check fails", 77, "77% · 4.2k", "7F7F7F"],
                            ["Fix by failure type", 83, "83% · 4.2k", "7F7F7F"],
                            ["Fact first, think on failure", 87, "87% · 2.5k", BLUE]], 0.7, 3.3, 1.5);
  [["79% = 79%", "fact found automatically = hand-written, on a benchmark never used before (MAMO)"],
   ["24 GB", "one RTX 3090-class GPU: gpt-oss-20b and Qwen3-14B match Qwen3-32B"],
   ["30", "labelled problems pick the best policy for a new task"]].forEach(([big, label], r) => {
    const y = 1.45 + r * 1.55;
    txt(s, big, 8.6, y, 4.1, 0.6, { fontSize: 30, bold: true, color: BLUE });
    txt(s, label, 8.6, y + 0.6, 4.1, 0.75, { fontSize: 14, valign: "top" });
  });
  caption(s, "\"Spend more on hard problems\" loses to \"facts first, think where the check fails\"");
  s.addNotes("Left: four ways to spend compute on the same 624 problems (Qwen3-8B, Qwen3-32B, Qwen3.6; same order on 3 seeds). Thinking on the hardest-looking problems, the compute-optimal scaling idea, gets 74% at 4.1k tokens; fact first and thinking only when the check fails gets 87% at 2.5k. Right: the fact needs no human (the model's own checked program for a similar problem: gpt-oss-20b 78.8% vs 78.9% hand-written on held-out MAMO); models that fit one 24 GB GPU match Qwen3-32B with the fact; 30 labelled problems choose the best policy for a new task (0.6 points from the best on average).");
  }
  const EXTRAS = [   // [index label, slide]
    ["Setup and fairness", () => slideSetup("Extra pages", "Extra: setup and fairness")],
    ["How hard: contest ranks, exams", () => slideKinds("Extra pages", "Extra: how hard, by contest ranks and exams")],
    ["Two versions, in detail", () => slideTwoVersions("Extra pages", "Extra: two versions catch each other's mistakes")],
    ["The examples check, in detail", () => slideHard("Extra pages", "Extra: think harder only when the examples fail")],
    ["Facts without a human, in detail", () => slideAuto("Extra pages", "Extra: the fact can be found without a human")],
    ["One fact helps small models most", () => slideSmall("Extra pages", "Extra: one fact helps small models most")],
    ["Reuse a checked program", () => slideReuse("Extra pages", "Extra: repeated problems need one checked program")],
    ["All policies, cost vs accuracy", () => slideTogether("Extra pages", "Extra: all policies, cost vs accuracy")],
    ["It pays off: small GPU, 30 labels", () => slidePays("Extra pages", "Extra: it pays off, even without a human or a big GPU")],
    ["Compared with published methods", () => slideBaselines("Extra pages", "Extra: compared with published methods")],
    ["Related research map", () => slideRelated("Extra pages", "Extra: where this work sits in related research")],
    ["Numbers reported in papers", () => slideReported("Extra pages", "Extra: numbers reported in papers, next to ours")],
    ["Proofs need a specialized model", () => slideProof("Extra pages", "Extra: proofs need a specialized model, not a fact")],
    ["Where the recipe stops", () => slideLimits("Extra pages", "Extra: where the recipe stops, and what is next")],
    ["All findings at a glance", () => slideGlance("Extra pages", "Extra: all findings at a glance")],
    ["Words we use", () => slideWords("Extra pages", "Extra: words we use")],
  ];
  s = pres.addSlide({ masterName: "Title Only", sectionTitle: "Talk" });
  s.addText("Thank you: questions?", { placeholder: "title" });
  txt(s, "Extra pages for questions (type the number and press Enter in the slide show)", 0.6, 1.4, 12.1, 0.45, { fontSize: 17, bold: true, color: BLUE });
  const first = pres.slides.length + 1;
  EXTRAS.forEach(([t], k) => {
    const x = 0.6 + (k % 4) * 3.05, y = 2.0 + Math.floor(k / 4) * 1.0;
    box(s, "", x, y, 2.9, 0.85, "F2F2F2");
    txt(s, [{ text: String(first + k), options: { bold: true, color: BLUE, fontSize: 20, breakLine: true } }, { text: t, options: { fontSize: 14 } }], x + 0.15, y, 2.65, 0.85, {});
  });
  s.addNotes(`End of the 5-minute talk; 5 minutes of questions follow. Extra pages (slides ${first}-${first + EXTRAS.length - 1}): ` + EXTRAS.map(([t], k) => `${first + k} ${t}`).join("; ") + ". Likely questions: why not GPT or Claude (open models only, cost and reproducibility); is the hand-written fact cheating (the automatic fact matches it); is the difference real (3 seeds, pre-registered); bigger model vs this recipe (small GPU page).");

  pres.addSection({ title: "Extra pages" });
  EXTRAS.forEach(([, make]) => make());

  pres.writeFile({ fileName: OUT }).then(async () => { await applyTheme(OUT, THEME); console.log("written", OUT); });
}
