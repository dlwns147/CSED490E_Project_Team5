// Proposal deck in the default Office look (white, Calibri Light / Calibri, Office accent colours).
const pptxgen = require("pptxgenjs");
const path = require("path");
// optional: writes the theme colours into the deck (from the pptx skill); without it the deck keeps the default Office theme
let applyTheme = async () => {};
try { ({ applyTheme } = require(process.env.PPTX_THEME_JS || "/root/.claude/skills/synced/3c05885e-4c45-4ba8-8aac-398768cdc097_763b3f05-13a5-417f-9a5f-72964acfee24/pptx/scripts/apply_theme.js")); } catch (e) {}

const ROOT = process.env.PROJECT_ROOT || path.join(__dirname, "..");   // repository root (this file is poc/make_slides.js)
const FIG = (f) => path.join(ROOT, "figs", f);
const ICON = (name) => FIG(path.join("icons", name + ".png"));   // figs/icons/*.png, drawn by poc/make_icons.js
const OUT = path.join(ROOT, "Proposal_Team5.pptx");

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
let WITH_MATH = true;   // false in the talk deck: competition math and proofs are left out of the talk for now (the full deck and PROPOSAL.md keep them)
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
slideTitle("Problem", "Team 5: Sangjun Lee, Seongbin Park · POSTECH CSED490E (Graduate NLP) · October 2026",
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
 ...(WITH_MATH ? [["sqrt", "Math and proofs", "AIME answers; Lean proofs of olympiad statements", "AIME: top ~5% of AMC; IMO gold: 25.9/30", "595959"]] : [])].forEach(([icon, head, ex, tag, col], k, all) => {
  const wide = all.length === 4, cw = wide ? 2.9 : 2.3, x = 0.6 + k * (cw + (wide ? 0.17 : 0.15));
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y: 1.3, w: cw, h: 2.35, rectRadius: 0.08, fill: { color: "F7F7F7" }, line: { color: "D9D9D9", width: 0.75 }, objectName: "kind " + head });
  s.addImage({ path: ICON(icon), x: x + 0.15, y: 1.42, w: 0.48, h: 0.48, objectName: "icon " + icon });
  txt(s, head, x + 0.7, 1.4, cw - 0.75, 0.55, { fontSize: wide ? 16 : 15, bold: true });
  txt(s, ex, x + 0.15, 2.0, cw - 0.3, 0.9, { fontSize: wide ? 14 : 13, valign: "top" });
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: x + 0.1, y: 2.95, w: cw - 0.2, h: 0.6, rectRadius: 0.1, fill: { color: "FFFFFF" }, line: { color: col, width: 1 }, objectName: "tag " + head });
  txt(s, tag, x + 0.15, 2.95, cw - 0.3, 0.6, { fontSize: wide ? 13 : 12.5, bold: true, color: col, align: "center" });
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
     [["task only", 23, "23%", G], ["think longer", 3, "3%", RED], ["long manual", 7, "7%", RED], ["exact usage", 83, "77–90%", BLUE]]);
mini(s, 1, "Small models gain most", "word problems: % solved",
     [["Qwen3-1.7B", 0.1, "0%", G], ["1.7B + fact", 44.5, "45%", BLUE], ["Qwen3-32B", 65.4, "65%", G], ["32B + fact", 66.2, "66%", BLUE]]);
mini(s, 2, "Compare two versions", "geometry, Qwen3-32B: % · tokens",
     [["8 extra tools", 59, "59% · 0.6k", RED], ["always think", 98, "98% · 5.9k", G], ["think if differ", 99, "99% · 4.3k", BLUE]]);
mini(s, 3, "Think only on failure", "311 contest problems: % · tokens",
     [["always high", 66.2, "66% · 30k", G], ["examples fail", 65.0, "65% · 20k", "5B9BD5"], ["+ brute force", 66.3, "66% · 25k", BLUE]]);
mini(s, 4, "Reuse a checked program", "48 routing days: % valid · tokens",
     [["new each day", 7, "7% · 86k", G], ["own notes", 36, "31–40%", G], ["reuse one", 94, "94% · 28k", BLUE]]);
mini(s, 5, "All together", "208 problems × 3 models: % · tokens",
     [["think on hardest", 74, "74% · 4.1k", G], ["fix by type", 83, "83% · 4.2k", G], ["fact first", 87, "87% · 2.5k", BLUE]]);
s.addNotes((pre || "") + "One panel per result. Add the fact: routing 23% to 77-90% (thinking longer 3%, long reference sheet 7%). Small models gain most: Qwen3-1.7B 0% to 45%, Qwen3-32B 65% to 66% (word problems). Compare two versions: 99% at 4.3k tokens vs always thinking 98% at 5.9k; with 8 extra tools 59%. Think only on a failed check (gpt-oss-120b, contest): 66.3% at 24.7k vs 66.2% at 30.1k. Reuse: 94% of 48 routing days vs 7% with a new program per day; Dynamic Cheatsheet (DC, the model's own notes) 31-40%. All together: fact first then think on failure 87% at 2.5k vs 74% at 4.1k for thinking on the hardest-looking problems (Snell-style) and 83% for choosing the fix by failure type.");
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
prompt(s, "Prompt B: task + the exact usage (11 lines)", ["...the task...", "dcb = r.RegisterUnaryTransitCallback(demand)", "r.AddDimensionWithVehicleCapacity(dcb, ...)"], 0.6, 3.3, 5.0, 1.15, "E2F0D9");
arrow(s, 5.6, 3.87, 6.0, 3.87);
code(s, "RegisterUnaryTransitCallback(...)", 6.0, 3.6, 4.6, 0.55, GREEN, 12);
txt(s, "✓ runs, best route", 10.75, 3.5, 2.0, 0.75, { fontSize: 15, bold: true, color: GREEN });
txt(s, "% of 30 routing problems solved optimally:", 0.6, 4.65, 12.1, 0.4, { bold: true, fontSize: 17 });
hbars(s, 0.6, 5.05, 12.1, [["Nothing extra", 23, "23%", "7F7F7F"], ["Think longer", 3, "3%", RED], ["Long reference sheet", 7, "7%", RED], ["Exact usage", 83, "77–90%", GREEN]], 0.38);
s.addNotes((pre || "") + "The model writes the program (the right side shows the line that matters). With a long reference sheet it guesses a plausible function name that does not exist and crashes; with the exact usage (11 lines) it writes the right one. Thinking longer cannot supply a fact it does not have (3%). On the 56 standard Solomon routing problems, three such facts together take gpt-oss-120b to a valid plan on every instance.");
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
txt(s, "Over 311 problems (gpt-oss-120b), with a quick brute-force check added: same 66% as always thinking hard, 18% fewer tokens", 0.6, 5.35, 12.1, 0.45, { fontSize: 17, bold: true });
hbars(s, 0.6, 5.8, 9.5, [["Always think hard", 100, "30k tokens", "7F7F7F"], ["Think hard only when a check fails", 82, "25k tokens", BLUE]], 0.4, 3.6);
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
pair(6.8, "208 problems × 3 models: % solved · tokens", [["think on hardest", 0.74, "74% · 4.1k", "7F7F7F"], ["our method", 0.87, "87% · 2.5k", BLUE]]);
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
txt(s, "Same 208 geometry and optimization problems × 3 models: % solved · tokens per problem", 0.6, 1.35, 12.1, 0.45, { fontSize: 18 });
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
    ["Contest geometry", "always high effort (reasoning-model default)", "66.2% · 30.1k", OURS("think when the examples or a brute-force check fail: 66.3% · 24.7k")],
    ["Pick 1 of 3 programs", "CodeT: the model writes tests", "96.0% (+340 tokens)", OURS("symmetry check: 99.7% (0 tokens)")],
    ["Library documentation", "DRoC: decompose, retrieve per constraint (ICLR 2025)", "72% · 2.1k", OURS("exact snippet: 77% · 1.7k")],
    ["Unneeded tools", "System 2 Attention / a \"use only if needed\" sentence", "64% / 76%", OURS("only the needed tools: 92%")],
    ["Daily routing", "Dynamic Cheatsheet: the model's own notes", "31–40%", OURS("reuse a checked program: 94%")],
    ["Word problems (held-out MAMO)", "ORLM-8B: a fine-tuned modeling specialist", "69.5% · 1.1k", OURS("Qwen3-8B, no training: 69.5% · 1.0k; gpt-oss-20b 78.8%")],
  ];
  table(s, rows, { x: 0.6, y: 1.45, w: 12.1, colW: [2.3, 3.9, 2.2, 3.7], rowH: 0.57, fontSize: 15 });
}
caption(s, "Measured here with the same problems and models: the recipe is more accurate, cheaper, or both");
s.addNotes((pre || "") + "All baselines were run by us on our benchmarks. Models: U1 policies over Qwen3-8B / Qwen3-32B / Qwen3.6 (208 problems × 3 models); contest geometry gpt-oss-120b (311); selection Qwen3-8B (300 geometry instances, 3 candidates); documentation Qwen3-32B on CVRP; tools Qwen3-32B on 5 geometry tasks; daily routing gpt-oss-120b on 48 held-out Solomon instances. Tokens are output tokens per problem. ORLM-LLaMA-3-8B was run in our harness on MAMO (863 held-out word problems; greedy 80.5 / 35.5% on Easy / Complex, as reported). More rows (MBR-exec, majority vote, DeepConf, Self-Debugging, Mixture-of-Thought cascade, BM25 retrieval) are in PROPOSAL.md section 6.");
}
slideBaselines("Method", "Compared with published methods");

// 9c. Related research: where this work sits, and numbers reported in papers
function slideRelated(section, title, pre) {
s = pres.addSlide({ masterName: "Title Only", sectionTitle: section });
s.addText(title, { placeholder: "title" });
const ADD = (t) => ({ text: t, options: { color: "38761D" } });
table(s, [
  [HDR("Theme"), HDR("Closest work"), HDR("What we add")],
  ["Programs instead of text", "PAL, Program-of-Thoughts, Mixture-of-Thought (ICLR 2024)", ADD(WITH_MATH ? "when a program helps; text vs program as a free check" : "a program for computation; two versions of it as a free check")],
  ["Library facts for code", "DRoC (ICLR 2025), CP-Bench, CloudAPIBench, DRAFT", ADD("an exact snippet beats the manual and thinking; facts mined without a human")],
  ["Misleading context", "Invisible Lottery (2606.04057), unneeded tools (2609.14157), CodeCrash, S2A", ADD("the harm on exact geometry, turned into a check")],
  ["Choosing a program", "CodeT, MBR-exec, AlphaCode's example filter, DeepConf", ADD("symmetry check of one program: 99.7% vs CodeT 96.0%")],
  ["Spending test-time compute", "Snell et al. 2025, FrugalGPT, DART, Thinkless, AdaptThink", ADD("fact + execution check, no training: 87% vs 74%")],
  ["Optimization modeling", "ORLM, STORM, EVOM, OR-R1 (trained); OptiMUS, OptiSkill (agents)", ADD("training-free, no answers; matches fine-tuned ORLM-8B")],
  ["One program, many instances", "FunSearch, HeuriGym, ARS, 2605.14141", ADD("measured 7% → 94%; edit a verified program for new rules")],
  ...(WITH_MATH ? [["Proofs", "Goedel-Prover-V2, DeepSeek-Prover-V2, AlphaGeometry", ADD("facts and checks do not carry over: use a specialized prover")]] : []),
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
  ...(WITH_MATH ? [
  ["miniF2F, 32 tries", "Goedel-Prover-V2-8B 84.6%", OURS("the same model in our harness: 76.6%")],
  ["IMO-AG-30 geometry", "AlphaGeometry 25 of 30; its symbolic engine alone 14; average IMO gold medallist 25.9, average participant 15.2", OURS("engine alone 12 in our setup; with our models' points 13")]] : []),
], { x: 0.6, y: 1.5, w: 12.1, colW: [2.4, 5.0, 4.7], rowH: [0.5, 1.3, 0.6, 0.9], fontSize: 15 });
caption(s, "Different harnesses and graders: for orientation only");
s.addNotes((pre || "") + "Numbers as reported by the papers or model cards; our harness, prompts and graders differ (MAMO labels are noisy; reported ORLM numbers range 81.6-88.2% on Easy). ORLM-8B rerun in our harness gives 80.5 / 35.5%, close to its report. STORM-Qwen3-4B is being run in our harness. Goedel-Prover-V2-8B: 187 of 244 with 32 tries in our Lean setup vs 84.6% on its card. AlphaGeometry's DD+AR engine proves 12 of IMO-AG-30 here (14 in the paper; one problem does not parse in this engine version).");
}
slideReported("Method", "Numbers reported in papers, next to ours");

// 9d. Setup and fairness (models, benchmarks, scoring, how comparisons are kept fair)
function slideSetup(section, title, pre) {
s = pres.addSlide({ masterName: "Title Only", sectionTitle: section });
s.addText(title, { placeholder: "title" });
[["robot", "Models", "open models run locally: Qwen3 1.7B–32B, Qwen3.6-35B, gpt-oss-20b and 120b" + (WITH_MATH ? "; Goedel- and DeepSeek-Prover for proofs" : "")],
 ["shapes", "Benchmarks", "13 geometry and 8 optimization tasks (generated); 311 Codeforces geometry; 56 Solomon routing; 82 job-shop; 1,208 word problems (NL4OPT, IndustryOR, MAMO)" + (WITH_MATH ? "; MATH-500 + AIME; miniF2F" : "")],
 ["check", "Exact scoring", "geometry right on all 8 moved copies; plans obey every rule; contest programs pass all official tests; " + (WITH_MATH ? "math and word problems" : "word problems") + " by exact answer"],
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
   ...(WITH_MATH ? ["Proofs: a skill, not a fact (use a specialized prover)"] : []),
   "Automatic facts only within one kind of problem",
   "Checks leak: 24–37% of wrong contest programs pass the examples",
   "Missing world knowledge: thinking adds 2–5 points at 70–200× tokens"]],
 ["Next", BLUE, [
   "Finish the held-out MAMO test (more models, 3 seeds)",
   "Errors no check catches: a perfect check adds only 1–3 points on word problems; the rest run but model the problem wrong",
   "Automatic facts for each problem type; final report"]]].forEach(([head, col, items], i) => {
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

// ================= 5-minute talk + 5 minutes of questions (Proposal_Team5.pptx): 9 slides, then extra pages for expected questions =================
function buildTalk() {
  pres = newDeck();
  WITH_MATH = false;
  const addSlide = pres.addSlide.bind(pres);   // notes only on the 9 talk slides (Korean script, SCRIPT_KO); the extra pages drop the full deck's notes
  // beginners read "a code hint" where the full deck and PROPOSAL.md say "a fact"; every text, table and chart label of the talk passes through term()
  const TERMS = [["A fact, a check, or more thinking", "A hint, a check, or more thinking"], ["a missing fact", "a code hint"],
                 ["give the fact, not the manual", "give a short hint, not the manual"], ["give the missing fact first", "give a short hint first"],
                 ["Add the missing fact", "Add a code hint"], ["Thinking cannot supply a fact the model does not have", "Thinking cannot supply what the model does not know"],
                 ["Thinking cannot add a fact the model lacks", "Thinking cannot add what the model does not know"]];
  const term = t => typeof t !== "string" ? t : TERMS.reduce((u, [a, b]) => u.split(a).join(b), t)
    .replace(/\b3 seeds\b/g, "3 runs").replace(/\bseed 1\b/g, "one run").replace(/\bevery seed\b/g, "every run")
    .replace(/\bFacts\b/g, "Hints").replace(/\bfacts\b/g, "hints").replace(/\bFact\b/g, "Hint").replace(/\bfact\b/g, "hint");
  const termText = x => Array.isArray(x) ? x.map(r => ({ ...r, text: term(r.text) })) : term(x);
  const termCell = c => typeof c === "string" ? term(c) : (c && typeof c === "object" ? { ...c, text: termText(c.text) } : c);
  pres.addSlide = (o) => {
    const sl = addSlide(o), text = sl.addText.bind(sl), tab = sl.addTable.bind(sl), chart = sl.addChart.bind(sl);
    sl.say = sl.addNotes.bind(sl); sl.addNotes = () => sl;
    sl.addText = (t, op) => text(termText(t), op);
    sl.addTable = (rows, op) => tab(rows.map(r => r.map(termCell)), op);
    sl.addChart = (type, data, op) => chart(type, Array.isArray(data) ? data.map(d => d && d.labels ? { ...d, name: term(d.name), labels: d.labels.map(term) } : d) : data, op);
    return sl;
  };
  const SCRIPT_KO = [   // speaker notes of slides 1-9 (seconds at a calm pace in brackets; about 4.5 minutes spoken)
    "(10초) 안녕하세요, 5조입니다. LLM으로 계산 수학 문제를 정확하고 싸게 푸는 방법을 제안합니다. 추가 노력을 힌트, 검사, 생각 중 어디에 써야 할까요?",
    "(25초) 저희가 푸는 문제는 네 종류입니다. 기하와 Codeforces 경시 문제는 맞는 알고리즘이, 배송 경로와 최적화 문장제는 솔버를 맞게 부르는 법이 필요합니다. 경시 문제의 중앙값은 Codeforces Master 수준입니다. 답이 정확히 하나라 코드로 채점할 수 있고, 필요한 것이 서로 달라서 추가 노력을 어디에 쓸지 비교하기 좋습니다.",
    "(15초) LLM은 말로 답할 수도, 프로그램을 짤 수도 있습니다. 같은 도형을 옮기고 돌리면 말로 한 답은 매번 바뀌지만, 프로그램은 항상 436입니다. 그래서 계산은 프로그램에 맡깁니다.",
    "(25초) 하지만 두 가지가 문제입니다. 첫째, 프로그램은 조용히 틀립니다. 같은 문제에 보조 코드만 더하면 6 대신 0을 내고 에러도 없습니다. 없는 함수를 불러 죽기도 합니다. 둘째, 오래 생각하면 비쌉니다. gpt-oss-120b는 토큰을 4.4배 써서 9점을 더 얻습니다. 그래서 추가 노력을 힌트, 공짜 검사, 생각 중 어디에 쓸지가 저희 질문입니다.",
    "(30초) 첫 번째 발견입니다. 매뉴얼이 아니라 짧은 힌트를 주세요. 트럭 경로를 짜는 과제에 OR-Tools 사용법 열한 줄을 붙이면, Qwen3-32B가 맞는 함수를 불러 최적 경로를 찾습니다. 긴 참조 문서를 주면 없는 함수를 지어내 죽습니다. 30문제에서 아무것도 안 주면 23%, 오래 생각하면 3%, 짧은 힌트는 83%입니다. 힌트는 같은 종류의 다른 문제에서 검사를 통과한 가장 짧은 프로그램을 골라, 사람 없이 만듭니다.\n\n[참고, 읽지 않음] 모델은 답을 무작위로 뽑기 때문에 같은 실험도 돌릴 때마다 조금씩 다릅니다. 짧은 힌트 막대는 같은 실험을 세 번 돌린 평균입니다(77, 83, 90%). 나머지 막대는 한 번씩 돌린 결과입니다.",
    "(35초) 두 번째 발견입니다. 공짜 검사가 실패할 때만 생각하게 하세요. 문제에 '막대 3, 4, 5면 답 0'이라는 예제가 있으면, 모델 없이 우리 프로그램을 3, 4, 5로 돌려 봅니다. 0이 나오면 그대로 내고, 다르면 그 문제만 더 생각합니다. 예제가 없으면 프로그램을 두 번 짜서 비교합니다. 그러면 경시 문제에서 66%, 기하에서 99%로, 항상 생각할 때와 같은 정확도를 18에서 27% 적은 토큰에 얻습니다.",
    "(30초) 둘을 합친 것이 저희 방법입니다. 힌트를 붙여 쓰고, 검사하고, 실패할 때만 생각하고, 같은 종류가 다시 오면 재사용합니다. 실제 문제 하나에서는 힌트 없이 죽던 프로그램이 힌트로 바로 20000을 맞혀, 5.3k 대신 0.6k 토큰을 썼습니다. 기하와 최적화 208문제를 세 모델로 풀면, 답이 갈리는 문제에 생각을 몰아주는 기존 방식은 74%, 저희는 87%이고 토큰도 적습니다.",
    "(35초) 새로운 점은 세 가지입니다. 학습 없이 공짜 검사로 생각할 때를 정하고, 정답 없이 모델 자신의 프로그램을 힌트로 쓰며, 파인튜닝한 특화 모델 ORLM-8B와 같은 69.5%를 학습하지 않은 8B 모델로 냅니다. 다음으로는 더 많은 모델로 검증하고, 실행은 되지만 문제를 잘못 수식으로 옮긴 오류를 다루고, 문제 종류마다 힌트를 찾겠습니다. 정리하면, 짧은 힌트를 먼저 주고, 공짜 검사가 실패한 곳에서만 생각하게 하자는 것입니다.\n\n[더 자세히: 질문이 나오거나 시간이 남을 때]\n첫째 줄, 생각을 어디에 쓸지. 기존 방법은 어려워 보이는 문제에 계산을 더 쓰는 Snell 등의 방식과, 언제 생각할지를 강화학습으로 가르치는 Thinkless, AdaptThink입니다. 저희는 정답 없이 돌리는 공짜 검사가 실패한 문제에만 생각을 씁니다. 기하와 최적화 208문제를 세 모델로 풀면 74%가 87%로 오르고, 토큰은 문제당 4.1k에서 2.5k로 줄었습니다. 87%는 사람이 쓴 힌트를 쓴 결과이고, 검색으로 찾은 힌트로도 84%입니다.\n둘째 줄, 모델에게 무엇을 주는지. 기존에는 매뉴얼 전체를 주거나, 더 큰 교사 모델이 짜서 정답으로 확인한 프로그램 모음을 줍니다. 저희 힌트는 모델이 다른 문제에서 짜서 공짜 검사를 통과한 자기 프로그램입니다. 끝까지 남겨 둔 MAMO 벤치마크에서 사람이 쓴 힌트와 같은 79%를 냈습니다.\n셋째 줄, 비용. ORLM-8B는 최적화 문장제용으로 파인튜닝한 공개 모델이고, 모델 카드의 형식과 솔버, 그리디 디코딩으로 저희 채점기에서 돌렸습니다: MAMO 69.5%, 문제당 1.1k 토큰(샘플링하면 64~66%). Qwen3-8B는 학습 없이 자기 힌트를 붙여 프로그램을 한 번 짜고 실행이 안 될 때만 생각하게 해서 69.5%, 1.0k 토큰입니다. 두 버전 검사까지 쓰면 71%(3.1k), gpt-oss-20b는 78.8%입니다.\n다음 계획. 하나, MAMO 검증을 Qwen3-32B와 Qwen3.6까지 세 시드로 마칩니다. 둘, 검사로 못 잡는 오류입니다. 지금 남은 오류의 절반쯤은 정답 라벨이 의심스러운 문제이고, 나머지는 같은 유형에서 같은 수식 실수가 반복됩니다. 예를 들어 순서 제약이나 공급 균형을 잘못 씁니다. 고치기 한 번이나 생각으로는 안 고쳐져서, 힌트 하나로 고쳐지는지 시험합니다. 셋, 지금은 같은 종류의 문제 안에서만 자동 힌트가 통하므로, 문제 종류마다 힌트를 찾고 최종 보고서와 코드를 냅니다.",
    "(5초) 감사합니다. 질문 받겠습니다.",
  ];
  const QA_KO = {   // speaker notes of the extra pages: a short Korean answer to the page's question
    howhint: "(답변) 힌트는 문제마다가 아니라 문제 종류마다 하나이고, 과제 앞에 붙여 줍니다. 그 종류에 필요한 호출만 보여 줍니다. 얻는 방법은 세 가지입니다. 첫째, 사람이 종류마다 한 번 씁니다. 트럭 경로라면 OR-Tools 사용법 11줄입니다. 둘째, 제목이 붙은 코드 조각 라이브러리에서 BM25로 검색해 맨 위 하나를 씁니다. 손으로 쓴 것과 거의 같지만, 비슷하지만 다른 문서가 섞이면 크게 떨어집니다. 셋째, 모델이 같은 종류의 다른 문제에서 짠 프로그램 중 공짜 검사를 통과한 가장 짧은 것을 씁니다. 처음 쓰는 MAMO에서 사람이 쓴 힌트와 같은 정확도였습니다. 다만 같은 종류 안에서만 통하고, 다른 종류의 프로그램을 주면 14에서 21점 떨어집니다. 필요한 것만 주는 것도 중요해서, 기하에서 도우미 함수를 다 주면 75%, 필요한 것만 주면 92%였습니다.",
    why: "(답변) 세 가지 이유입니다. 답이 정확히 하나라 코드로 채점할 수 있고, 정답 없이 쓸 수 있는 검사가 있으며, 실제 코딩 에이전트가 이미 경로 계획, 스케줄러, 기하 코드를 씁니다. 그리고 종류마다 필요한 것이 다릅니다. 기하와 경시는 맞는 알고리즘이 필요하고, 둘의 차이는 난이도입니다. 경로와 문장제는 솔버 라이브러리를 맞게 부르는 힌트가 필요하고, 문장제는 글을 수식으로 옮기는 단계가 더 있습니다. 그래서 추가 노력을 힌트, 검사, 생각 중 어디에 쓸지 비교하기 좋습니다.",
    coverage: "(답변) 아니요, 모든 단계를 네 종류 전부에 쓰지는 않습니다. 경시 문제는 라이브러리 없이 알고리즘만 짜는 문제라 힌트로 채울 빈칸이 없고, 실패 원인은 추론입니다. 가장 가까운 힌트로 관련 기하 함수 8개를 줘 봤는데, Qwen3-32B는 12.1%에서 13.7%로 차이가 없었고 gpt-oss-20b는 37.7%에서 33.4%로 오히려 떨어졌습니다. 함수를 받으면 덜 생각하고 다른 오답을 썼습니다. 문제마다 알고리즘을 알려 주는 힌트는 사실상 풀이의 일부라 싸지도 자동도 아닙니다. 그래서 경시에는 검사와 생각만 써서, 항상 생각할 때와 같은 66%를 18% 적은 토큰에 얻습니다. 재사용도 매번 새 문제라 맞지 않습니다.",
    kinds: "(답변) 사람 기준으로 보면, 경시 문제 311개의 Codeforces 레이팅 중앙값은 2200으로 Master 수준이고, 46%는 Grandmaster 수준인 2400 이상입니다. 그 구간에서는 gpt-oss-120b도 48%만 풉니다. 경로 문제는 단순한 탐욕 계획이 최선보다 48% 길고, 문장제는 대학 OR 수업 연습문제 수준입니다.",
    two: "(답변) 보조 코드를 주면 모델이 그 함수에 맞춰 방법을 짭니다. 이 예에서는 필요 없는 polar_sort로 각도 정렬을 하다가 0을 출력했습니다. 기하 108문제에서 보조 코드가 있으면 59%, 없으면 77%입니다. 두 버전을 모두 짜서 답이 다를 때만 생각하면 99%를 4.3k 토큰에 얻습니다.",
    fact: "(답변) 힌트는 라이브러리를 어떻게 부르는지, 즉 함수 이름과 인자를 보여 주는 11줄짜리 코드 조각입니다. 같은 종류의 30문제에 똑같이 붙이고, 경로나 숫자나 정답은 들어 있지 않습니다. 긴 참조 문서가 아무것도 안 준 것보다 나쁜 이유는, 경로 설명은 있지만 용량 규칙이 없어서 모델이 빈 곳을 없는 함수로 채우기 때문입니다. 10개 프로그램이 RegisterUnaryLongLivingCallback을 불렀습니다.",
    rag: "(답변) 네. 제목이 붙은 코드 조각 라이브러리에서 BM25로 찾으면, 최적화 6문제에서 손으로 쓴 힌트와 같은 수준입니다. 97% 대 96%입니다. 다만 비슷하지만 다른 문서가 섞이면 손해가 큽니다. 경로 문제에서 TSP 문서가 함께 들어오면 83%에서 57%로 떨어집니다. 문서가 아예 없으면 모델 자신의 검사된 프로그램을 힌트로 씁니다.",
    think: "(답변) 모르는 함수를 생각하는 동안 지어내기 때문입니다. Qwen3-32B는 문장제에서 생각을 켜면 65.4%에서 52.0%로 떨어지는데, 존재하지 않는 Objective().SetMaximize를 부릅니다. 정확한 사용법을 먼저 주면 생각이 도움이 되어 72%가 되고, 실패할 때만 생각하면 같은 정확도를 1.3k 토큰에 냅니다.",
    leak: "(답변) 생깁니다. 경시 문제에서는 틀린 프로그램의 24에서 37%가 예제를 통과하고, 문장제에서는 12에서 16%가 두 프로그램이 같은 오답을 냅니다. 하지만 이런 문제를 완벽한 검사로 모두 생각에 보내도 생각이 7에서 16%만 고치기 때문에, 14B 이상 모델에서는 1에서 3점밖에 오르지 않습니다. 일부는 정답 레이블 자체가 틀렸습니다. 그래서 다음 목표는 실행은 되지만 문제를 잘못 모델링한 프로그램입니다.",
    checks: "(답변) 저희가 다룬 네 종류에는 모두 정답 없이 쓸 수 있는 검사가 있습니다. 경시는 예제와 모든 경우를 따지는 짧은 프로그램, 기하는 입력을 옮기거나 돌려도 답이 같아야 한다는 검사나 두 버전의 일치, 경로는 계획이 모든 규칙을 지키는지 코드로 확인, 문장제는 두 프로그램의 일치입니다. 검사가 얼마나 잡아내느냐가 생각을 얼마나 아낄지를 정합니다.",
    auto: "(답변) 사람이 쓰지 않습니다. 모델이 다른 문제에서 짜서 공짜 검사를 통과한 자기 프로그램 중 가장 짧은 것을 힌트로 붙입니다. 끝까지 쓰지 않고 남겨 둔 MAMO 863문제에서 세 모델 모두 사람이 쓴 힌트와 약 2점 안에 들었습니다. 단, 다른 종류의 문제에서 가져온 프로그램은 오히려 14에서 21점 손해이고, 라이브러리 이름 목록만 주면 66%에서 56%로 떨어집니다.",
    hard: "(답변) 오히려 강한 기준선을 만들어 봤습니다. 각 문제의 실제 Codeforces 레이팅을 알려 주고 어려운 문제만 높은 노력으로 보내도 예제 검사보다 못합니다. 레이팅 2600 이상만 보내면 61.4%, 1800 이상이면 65.3%인데 토큰이 27.8k로, 예제 검사의 65.0%, 20.2k보다 비쌉니다. 이 분석은 탐색적이라 사전 등록은 하지 않았습니다. 기하와 최적화에서도 난이도 기준 배분은 74%, 저희 방법은 87%입니다.",
    published: "(답변) 같은 문제와 같은 모델로 기존 방법을 직접 돌려 비교했습니다. 난이도별 생각 배분은 74%, 4.1k 대 저희 87%, 2.5k이고, 항상 높은 노력은 66.2%, 30.1k 대 66.3%, 24.7k이고, 모델이 테스트를 쓰는 CodeT는 96.0% 대 대칭 검사 99.7%입니다. 특화 모델 ORLM-8B의 69.5%는 학습 없는 Qwen3-8B도 같은 69.5%입니다. 저희 방법은 더 정확하거나, 더 싸거나, 둘 다입니다.",
    related: "(답변) 관련 연구는 일곱 갈래입니다. 텍스트 대신 프로그램, 코드용 라이브러리 문서, 오도하는 문맥, 프로그램 고르기, 테스트 시간 계산 배분, 최적화 모델링, 한 프로그램 재사용입니다. 저희가 더하는 것은 실패 원인에 맞춰 힌트와 공짜 검사를 먼저 쓰고, 학습도 정답도 없이 생각을 아끼는 것입니다.",
    reported: "(답변) 논문 수치와 나란히 놓으면, MAMO Easy에서 학습 없는 Qwen3-14B가 82.8%로 파인튜닝한 ORLM의 82.3%와 비슷하고, gpt-oss-20b는 85.6%입니다. 프런티어 모델을 쓰는 OptiSkill의 90.8에서 94.3%보다는 낮습니다. 평가 환경이 달라서 참고용입니다.",
    vote: "(답변) 다수결은 많이 나온 답을 고르고, 검사는 맞는 답을 고릅니다. 기하에서 세 프로그램 중 하나를 고를 때 다수결은 4.3% 틀리고, 대칭 검사는 0.3%만 틀립니다. 문장제에서 생각 세 번의 다수결은 79.4%로 저희보다 7점 높지만, 토큰이 16.4k로 12배입니다.",
    fair: "(답변) 세 가지를 확인했습니다. 첫째, 입력 토큰입니다. 힌트 조각은 입력을 213토큰 늘리고, 입력은 출력보다 싸고 캐시되므로 결론이 바뀌지 않습니다. 다만 프로그램을 돌리는 CPU 시간은 세지 않았습니다. 둘째, 암기입니다. 같은 난이도에서 오래된 대회와 최근 대회의 정답률이 81% 대 83%로 차이가 없고, MAMO는 끝까지 쓰지 않았으며, 모든 방법이 같은 모델을 씁니다. 셋째, 작은 차이는 '더 낫다'가 아니라 '같은 정확도에 더 적은 토큰'이라고만 말합니다.",
    small: "(답변) 네, 작은 모델일수록 효과가 큽니다. 문장제 345문제에서 힌트 하나로 Qwen3-1.7B는 44점, 4B는 31점 오르고, 32B는 1점 오릅니다. 그래서 24GB GPU 한 장에 들어가는 gpt-oss-20b가 힌트와 함께 73%로, Qwen3-32B의 72%를 토큰 8분의 1로 따라잡습니다.",
    policies: "(답변) 기하와 최적화 208문제를 세 모델로 푼 정책 비교입니다. 힌트를 먼저 주고 실패할 때만 생각하는 정책이 87%, 2.5k로 가장 정확하고 가장 싼 편입니다. 새 과제라면 30문제만 라벨링해서 네 정책 중 고르면, 63개 설정에서 최선 대비 손실이 0.6점입니다. 이 정책을 기본값으로 쓰면 1.4점, 항상 생각하면 8.4점 손해입니다.",
    limits: "(답변) 방법이 멈추는 곳은 세 가지입니다. 다른 종류의 문제 사이의 자동 힌트, 예제를 통과하는 틀린 프로그램, 그리고 세계 지식이 필요한 문제입니다. 다음으로는 MAMO 검증을 더 많은 모델로 마치고, 검사로 못 잡는 문제 모델링 오류를 다루고, 문제 종류마다 자동 힌트를 찾겠습니다.",
    reuse: "(답변) 같은 종류의 문제가 데이터만 바뀌어 반복되면, 검사된 프로그램 하나를 재사용합니다. 배송 경로 48일 동안 매일 새 프로그램을 쓰면 7%의 날만 유효하고 86k 토큰이 듭니다. 16개 프로그램을 한 번 쓰고 지난 8일에 유효한 것을 재사용하면 94%의 날이 유효하고 모두 28k 토큰입니다. 4배 큰 입력에서도 통했고, 규칙이 바뀌면 모델에게 고치게 하면 됩니다.",
    setup: "(답변) 모델은 Qwen3 1.7B에서 32B, Qwen3.6-35B, gpt-oss-20b와 120b이고 모두 직접 돌렸습니다. 채점은 정확히 맞았는지만 보고, 모든 결과에 토큰 비용을 함께 적습니다. 예측을 먼저 적고 한 번에 하나만 바꾸며 3개 시드로 확인했습니다. GPU는 96GB 한 장이고, 작은 모델은 24GB 한 장에 들어갑니다.",
  };
  const CHOICES = [["fact", "a missing fact", "E2F0D9", "38761D"], ["check", "a free check", "E2F0D9", "38761D"], ["brain", "more thinking", "FADBD8", RED]];
  function pill(x, y, k, fs = 15) {   // choice k from "where should the extra effort go?"
    const [icon, t, fill, col] = CHOICES[k];
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w: 2.05, h: 0.55, rectRadius: 0.2, fill: { color: fill }, line: { color: col, width: 1 }, objectName: "choice " + t });
    s.addImage({ path: ICON(icon), x: x + 0.12, y: y + 0.095, w: 0.36, h: 0.36, objectName: "choice icon " + icon });
    txt(s, t, x + 0.55, y, 1.5, 0.55, { fontSize: fs, bold: true, color: col });
  }
  pres.addSection({ title: "Talk" });
  slideTitle("Talk", "Team 5: Sangjun Lee, Seongbin Park · POSTECH CSED490E", "");
  [0, 1, 2].forEach(k => pill(3.44 + k * 2.2, 5.35, k));

  // 2. what we solve, and how hard
  s = pres.addSlide({ masterName: "Title Only", sectionTitle: "Talk" });
  s.addText("What we solve, and how hard it is", { placeholder: "title" });
  [["needs the right algorithm", BLUE, 0.6], ["needs the right solver call", "38761D", 6.74]].forEach(([t, col, x]) => {   // the two families
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y: 1.35, w: 5.96, h: 0.42, rectRadius: 0.08, fill: { color: col }, line: { color: col }, objectName: "family " + t });
    txt(s, t, x, 1.35, 5.96, 0.42, { fontSize: 16, bold: true, color: "FFFFFF", align: "center" });
  });
  [["shapes", "Geometry", "corners of the rubber band around 10 points", "textbook algorithms, exact on every copy", BLUE],
   ["trophy", "Contest problems", "311 Codeforces geometry problems", "Codeforces Master to Grandmaster level", RED],
   ["truck", "Routing, scheduling", "routes for 100 customers with time windows", "a simple plan drives 48% farther", THEME.colors.accent2],
   ["calc", "Word problems", "most coins from 500 gold and 300 wires?", "university operations-research exercises", "38761D"]].forEach(([icon, head, ex, tag, col], k) => {
    const x = 0.6 + k * 3.07;
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y: 1.9, w: 2.9, h: 3.95, rectRadius: 0.08, fill: { color: "F7F7F7" }, line: { color: "D9D9D9", width: 0.75 }, objectName: "kind " + head });
    s.addImage({ path: ICON(icon), x: x + 1.05, y: 2.05, w: 0.8, h: 0.8, objectName: "icon " + icon });
    txt(s, head, x + 0.1, 2.95, 2.7, 0.5, { fontSize: 19, bold: true, align: "center" });
    txt(s, ex, x + 0.2, 3.5, 2.5, 1.0, { fontSize: 15, align: "center", valign: "top" });
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: x + 0.15, y: 4.7, w: 2.6, h: 0.95, rectRadius: 0.1, fill: { color: "FFFFFF" }, line: { color: col, width: 1.25 }, objectName: "tag " + head });
    txt(s, tag, x + 0.2, 4.7, 2.5, 0.95, { fontSize: 15, bold: true, color: col, align: "center" });
  });
  caption(s, "Why these: exact answers that code can grade, and each kind needs something different");

  // 3. one idea: let the computer do the arithmetic
  s = pres.addSlide({ masterName: "Title Only", sectionTitle: "Talk" });
  s.addText("Let the computer do the math", { placeholder: "title" });
  txt(s, "Qwen3-8B, asked for twice the area of one shape: moved, turned or flipped, it is always 436", 0.6, 1.35, 12.1, 0.45, { fontSize: 18, align: "center" });
  s.addImage({ path: FIG("slide2_shapes.png"), x: 3.9, y: 1.95, w: 8.8, h: 1.9, objectName: "four copies of one polygon", altText: "one polygon: original, moved, turned, flipped" });
  [["Answer in words", [["436 ✓", 1], ["2944 ✗", 0], ["392 ✗", 0], ["728 ✗", 0]], 4.25], ["Write a program", [["436 ✓", 1], ["436 ✓", 1], ["436 ✓", 1], ["436 ✓", 1]], 5.1]].forEach(([head, ans, y]) => {
    txt(s, head, 0.6, y, 3.2, 0.6, { fontSize: 22, bold: true });
    ans.forEach(([t, ok], k) => chip(s, t, ok, 3.9 + k * 2.2, y));
  });
  caption(s, "For computation, a program is the right tool");

  // 4. two problems, one example each, and the question
  s = pres.addSlide({ masterName: "Title Only", sectionTitle: "Talk" });
  s.addText("But two things go wrong", { placeholder: "title" });
  function pane3(x, head, col, fill) {
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y: 1.35, w: 5.95, h: 4.15, rectRadius: 0.08, fill: { color: fill }, line: { color: col, width: 1 }, objectName: "pane " + head });
    txt(s, head, x + 0.25, 1.45, 5.45, 0.55, { fontSize: 22, bold: true, color: col });
  }
  pane3(0.6, "1. Programs fail, often silently", RED, "FDF2F1");
  txt(s, "How many corners does the rubber band have?", 0.85, 2.05, 5.5, 0.4, { fontSize: 15 });
  s.addImage({ path: FIG("slide5_hull.png"), x: 0.95, y: 2.5, w: 2.0, h: 2.0, objectName: "ten points and their hull", altText: "10 points; the rubber band touches 6 of them" });
  txt(s, "answer: 6 corners", 0.75, 4.5, 2.4, 0.35, { fontSize: 15, bold: true, color: GREEN, align: "center" });
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 3.25, y: 2.55, w: 3.1, h: 1.55, rectRadius: 0.05, fill: { color: "262626" }, line: { color: "262626" }, objectName: "terminal" });
  s.addText([{ text: "program A  → 6", options: { color: "8FD16A", bold: true, breakLine: true } },
             { text: "program B  → 0", options: { color: "FF7B7B", bold: true, breakLine: true } },
             { text: "no error message", options: { color: "BFBFBF" } }],
    { isTextBox: true, x: 3.45, y: 2.55, w: 2.8, h: 1.55, fontFace: "Courier New", fontSize: 18, valign: "middle", margin: 0 });
  txt(s, "B's prompt only added helper code (Qwen3-14B)", 3.25, 4.15, 3.1, 0.6, { fontSize: 14, color: C.text2, valign: "top" });
  txt(s, "✗ or it crashes on a library function that does not exist", 0.85, 4.95, 5.5, 0.4, { fontSize: 15, bold: true, color: RED });
  pane3(6.75, "2. Thinking longer is expensive", THEME.colors.accent2, "FDF0E6");
  txt(s, "311 contest problems, gpt-oss-120b · 1 page ≈ 700 tokens", 7.0, 2.05, 5.5, 0.4, { fontSize: 15 });
  [["normal", "57% solved", 10, "page", 2.6], ["think hard", "66% solved", 43, "pagehot", 3.35]].forEach(([lab, acc, n, icon, y]) => {
    txt(s, [{ text: lab, options: { bold: true, breakLine: true } }, { text: acc }], 7.0, y, 1.6, 0.65, { fontSize: 15 });
    for (let k = 0; k < n; k++) s.addImage({ path: ICON(icon), x: 8.65 + (k % 18) * 0.21, y: y + 0.02 + Math.floor(k / 18) * 0.24, w: 0.2, h: 0.22, objectName: `${lab} page ${k}` });
  });
  txt(s, [{ text: "4.4× the pages", options: { bold: true, fontSize: 24, color: THEME.colors.accent2 } }, { text: "  for 9 more points", options: { fontSize: 17 } }],
      7.0, 4.65, 5.6, 0.6, {});
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 0.6, y: 5.75, w: 12.1, h: 0.9, rectRadius: 0.08, fill: { color: "DEEBF7" }, line: { color: "BDD7EE", width: 0.75 }, objectName: "our question" });
  txt(s, "Our question: where should the extra effort go?", 0.85, 5.75, 5.5, 0.9, { fontSize: 19, bold: true, color: BLUE });
  [0, 1, 2].forEach(k => pill(6.25 + k * 2.15, 5.92, k));

  function costRows(x, y, w, labW, rows, maxTok = Math.max(...rows.map(r => r[2])), step = 0.58) {   // [label, % solved, tokens, tokens shown, colour]: the number is accuracy, the bar is cost
    const barX = x + labW + 1.0, barMax = w - labW - 1.0 - 0.8;
    txt(s, "solved", x + labW, y, 0.9, 0.35, { fontSize: 14, color: "7F7F7F", align: "center" });
    txt(s, "tokens per problem", barX, y, barMax + 0.8, 0.35, { fontSize: 14, color: "7F7F7F" });
    rows.forEach(([lab, acc, tok, shown, col], r) => {
      const yy = y + 0.4 + r * step, bw = barMax * tok / maxTok;
      txt(s, lab, x, yy, labW - 0.1, 0.5, { fontSize: 15, align: "right" });
      txt(s, acc, x + labW, yy, 0.9, 0.5, { fontSize: 17, bold: true, color: col, align: "center" });
      s.addShape(pres.shapes.RECTANGLE, { x: barX, y: yy + 0.11, w: bw, h: 0.28, fill: { color: col }, line: { color: col, width: 0.5 }, objectName: "tokens " + lab });
      txt(s, shown, barX + bw + 0.1, yy, 0.8, 0.5, { fontSize: 15, bold: true, color: col });
    });
  }

  const KINDS = ["shapes", "trophy", "truck", "calc"];   // the four kinds of slide 2, in order
  function holdsOn(on) {   // faded: not tested there, or it does not hold (detail on the coverage page)
    txt(s, "holds on", 9.6, 1.08, 1.25, 0.3, { fontSize: 14, color: "7F7F7F", align: "right" });
    KINDS.forEach((icon, k) => s.addImage({ path: ICON(icon), x: 11.0 + k * 0.42, y: 1.07, w: 0.3, h: 0.3, transparency: on.includes(icon) ? 0 : 82,
                                            objectName: (on.includes(icon) ? "holds on " : "not shown on ") + icon }));
  }

  function answerBadge(ks) {   // the matching choice(s), top right
    ks.forEach((k, j) => pill(12.7 - (ks.length - j) * 2.15, 0.52, k, 14));
  }

  // 5. finding 1
  s = pres.addSlide({ masterName: "Title Only", sectionTitle: "Talk" });
  s.addText("Finding 1: give the fact, not the manual", { placeholder: "title" });
  answerBadge([0]);
  holdsOn(["shapes", "truck", "calc"]);
  // left: how the hint is given, on the real routing task; right: what it buys
  panel(s, 0.6, 1.5, 5.85, 4.55, "how the hint is given");
  txt(s, "How the hint is given (Qwen3-32B, OR-Tools)", 0.85, 1.58, 5.4, 0.42, { fontSize: 18, bold: true, color: BLUE });
  box(s, "Task: plan routes for trucks with a weight limit", 0.85, 2.05, 5.35, 0.5, "FFFFFF", { fontSize: 15 });
  txt(s, "+", 3.4, 2.55, 0.3, 0.25, { fontSize: 16, bold: true, align: "center" });
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 0.85, y: 2.8, w: 5.35, h: 1.05, rectRadius: 0.06, fill: { color: "E2F0D9" }, line: { color: "38761D", width: 1 }, objectName: "the hint" });
  s.addText([{ text: "Hint: the exact usage, 11 lines, e.g.", options: { bold: true, color: "38761D", fontFace: THEME.bodyFontFace, breakLine: true } },
             { text: "r.RegisterUnaryTransitCallback(demand)", options: { breakLine: true } },
             { text: "r.AddDimensionWithVehicleCapacity(...)" }],
    { isTextBox: true, x: 1.0, y: 2.82, w: 5.1, h: 1.0, fontFace: "Courier New", fontSize: 14, color: C.text1, valign: "middle", margin: 0 });
  arrow(s, 3.52, 3.85, 3.52, 4.05);
  box(s, "✓ the program runs: best route", 0.85, 4.05, 5.35, 0.45, "E2F0D9", { fontSize: 15, bold: true, color: "38761D" });
  txt(s, "A long reference sheet instead (no weight rule in it):", 0.85, 4.62, 5.35, 0.35, { fontSize: 15, bold: true });
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 0.85, y: 5.0, w: 5.35, h: 0.85, rectRadius: 0.06, fill: { color: "FADBD8" }, line: { color: RED, width: 1 }, objectName: "invented call" });
  s.addText([{ text: "RegisterUnaryLongLivingCallback()", options: { fontFace: "Courier New", breakLine: true } }, { text: "✗ invented, does not exist: crash", options: { bold: true } }],
    { isTextBox: true, x: 1.0, y: 5.0, w: 5.1, h: 0.85, fontSize: 14, color: RED, valign: "middle", margin: 0 });
  panel(s, 6.75, 1.5, 5.95, 4.55, "what it buys");
  txt(s, "Result: 30 routing problems solved optimally", 7.0, 1.58, 5.45, 0.42, { fontSize: 18, bold: true, color: BLUE });
  hbars(s, 7.0, 2.1, 5.45, [["task only", 23, "23%", "7F7F7F"], ["+ think longer", 3, "3%", RED], ["+ long sheet", 7, "7%", RED], ["+ short hint", 83, "83%", BLUE]], 0.55, 1.75, 1.9);
  // how we pick the hint, once per problem type, with no human: the model's own shortest check-passing program
  txt(s, "How we pick the hint (per problem type, no human):", 7.0, 4.5, 5.45, 0.38, { fontSize: 15, bold: true });
  [["its past programs", "FFFFFF", C.text1], ["✓ passed the check", "FFFFFF", C.text1], ["shortest = hint", "E2F0D9", "38761D"]].forEach(([t, fill, col], k) => {
    const x = 7.0 + k * 1.92;
    box(s, t, x, 5.0, 1.6, 0.62, fill, { fontSize: 15, bold: k === 2, color: col });
    if (k < 2) arrow(s, x + 1.6, 5.31, x + 1.92, 5.31);
  });
  caption(s, "Thinking cannot supply what the model does not know: give it the hint");

  // 6. finding 2: free checks decide when to think
  s = pres.addSlide({ masterName: "Title Only", sectionTitle: "Talk" });
  s.addText("Finding 2: think only when a free check fails", { placeholder: "title" });
  answerBadge([1]);
  holdsOn(["shapes", "trophy", "truck", "calc"]);
  // left: how a free check runs, on one real example; right: what it buys
  panel(s, 0.6, 1.5, 5.85, 4.55, "how a free check works");
  txt(s, "How a free check works", 0.85, 1.58, 5.4, 0.42, { fontSize: 18, bold: true, color: BLUE });
  box(s, "The problem shows an example: sticks 3 4 5 → answer 0", 0.85, 2.05, 5.35, 0.62, "FFFFFF", { fontSize: 15 });
  arrow(s, 3.52, 2.67, 3.52, 2.9);
  box(s, "Run our program on 3 4 5 (no model needed): it prints 0", 0.85, 2.9, 5.35, 0.62, "FFFFFF", { fontSize: 15 });
  arrow(s, 2.3, 3.52, 2.1, 3.78); arrow(s, 4.75, 3.52, 4.95, 3.78);
  box(s, "✓ same → submit (no extra tokens)", 0.85, 3.78, 2.6, 0.72, "E2F0D9", { fontSize: 15, bold: true, color: "38761D" });
  box(s, "✗ different → think harder, write again", 3.6, 3.78, 2.6, 0.72, "FADBD8", { fontSize: 15, bold: true, color: RED });
  txt(s, "No example? Write the program twice, compare:", 0.85, 4.68, 5.35, 0.4, { fontSize: 15, bold: true });
  box(s, "version A prints 6", 0.85, 5.15, 1.6, 0.6, "FFFFFF", { fontSize: 14 });
  box(s, "version B prints 0", 2.55, 5.15, 1.6, 0.6, "FFFFFF", { fontSize: 14 });
  arrow(s, 4.15, 5.45, 4.4, 5.45);
  box(s, "✗ different → think", 4.4, 5.15, 1.8, 0.6, "FADBD8", { fontSize: 14, bold: true, color: RED });
  panel(s, 6.75, 1.5, 5.95, 4.55, "what it buys");
  txt(s, "Result: the same accuracy, fewer tokens", 7.0, 1.58, 5.45, 0.42, { fontSize: 18, bold: true, color: BLUE });
  txt(s, "311 contest problems (gpt-oss-120b)", 7.0, 2.02, 5.45, 0.32, { fontSize: 15, bold: true });
  costRows(7.0, 2.3, 5.45, 2.45, [["always think hard", "66.2%", 30.1, "30k", "7F7F7F"], ["think only on failure", "66.3%", 24.7, "25k", BLUE]], undefined, 0.48);
  txt(s, "examples alone give 65.0% at 20k; adding a brute-force program as a second check gives 66.3%", 7.0, 3.68, 5.45, 0.5, { fontSize: 14, color: C.text2, valign: "top" });
  txt(s, "108 geometry problems (Qwen3-32B)", 7.0, 4.3, 5.45, 0.32, { fontSize: 15, bold: true });
  costRows(7.0, 4.58, 5.45, 2.45, [["always think", "98%", 5.9, "5.9k", "7F7F7F"], ["think only on failure", "99%", 4.3, "4.3k", BLUE]], undefined, 0.48);
  caption(s, "Same accuracy as always thinking, 18–27% fewer tokens, and no answer key needed");

  // 7. the method on one problem, and what it gives overall
  s = pres.addSlide({ masterName: "Title Only", sectionTitle: "Talk" });
  s.addText("Our method: cheap steps first", { placeholder: "title" });
  answerBadge([0, 1]);
  txt(s, "icons: where each step is used", 9.0, 1.08, 3.7, 0.3, { fontSize: 14, color: "7F7F7F", align: "right" });
  [["① program + hint", "F2F2F2", C.text1, ["shapes", "truck", "calc"]], ["② free check", "DEEBF7", "1F3864", KINDS],
   ["③ pass: submit · fail: think", "E2F0D9", "38761D", KINDS], ["④ same type again: reuse it", "F2F2F2", C.text1, ["truck"]]].forEach(([t, fill, col, used], k) => {
    const x = 0.6 + k * 3.07;
    box(s, t, x, 1.45, 2.85, 0.55, fill, { fontSize: 15, bold: true, color: col });
    if (k < 3) arrow(s, x + 2.85, 1.72, x + 3.07, 1.72);
    KINDS.forEach((icon, j) => s.addImage({ path: ICON(icon), x: x + 0.86 + j * 0.3, y: 2.07, w: 0.24, h: 0.24, transparency: used.includes(icon) ? 0 : 82,
                                            objectName: `step ${k + 1} ${used.includes(icon) ? "used on" : "not needed on"} ${icon}` }));
  });
  panel(s, 0.6, 2.5, 5.85, 3.55, "one real problem");
  txt(s, "One real problem (Qwen3-8B, a MAMO word problem)", 0.85, 2.56, 5.4, 0.4, { fontSize: 17, bold: true, color: BLUE });
  box(s, "Task: the minimum cost of products X, Y, Z under three limits (answer 20000)", 0.85, 3.0, 5.35, 0.6, "FFFFFF", { fontSize: 15 });
  box(s, "✗ no hint: it calls a function that does not exist → crash", 0.85, 3.7, 5.35, 0.55, "FADBD8", { fontSize: 15, color: RED });
  box(s, "✓ hint = its own checked program from another problem: both versions print 20000 → submit", 0.85, 4.35, 5.35, 0.8, "E2F0D9", { fontSize: 15, color: "38761D" });
  txt(s, [{ text: "0.6k tokens", options: { bold: true, color: BLUE } }, { text: "  (thinking alone: 5.3k)" }], 0.85, 5.3, 5.35, 0.45, { fontSize: 17 });
  panel(s, 6.75, 2.5, 5.95, 3.55, "overall result");
  txt(s, "208 geometry + optimization problems × 3 models", 7.0, 2.56, 5.45, 0.4, { fontSize: 17, bold: true, color: BLUE });
  costRows(7.0, 2.98, 5.45, 2.5, [["think where answers differ", "74%", 4.1, "4.1k", "7F7F7F"], ["ours, hint found by search", "84%", 3.3, "3.3k", "5B9BD5"], ["ours, hand-written hint", "87%", 2.5, "2.5k", BLUE]], undefined, 0.5);
  txt(s, "Held-out MAMO (863): the model's own program as the hint = a hand-written one (79% = 79%, gpt-oss-20b)", 7.0, 4.95, 5.45, 0.9, { fontSize: 14, color: C.text2, valign: "top" });
  caption(s, "More accurate and cheaper than spending thinking on the hardest-looking problems");

  // 8. what is new (the usual way vs ours, row by row), what is next (a timeline), and the takeaway
  s = pres.addSlide({ masterName: "Title Only", sectionTitle: "Talk" });
  s.addText("What is new, and what is next", { placeholder: "title" });
  txt(s, "The usual way", 2.3, 1.3, 4.6, 0.4, { fontSize: 16, bold: true, color: "7F7F7F", align: "center" });
  txt(s, "Ours", 7.6, 1.3, 5.1, 0.4, { fontSize: 16, bold: true, color: BLUE, align: "center" });
  [["When to think", "brain", "think more on hard-looking problems, or train the model when to think", "check", "think only when a free check fails; no training: 87% vs 74% (208 problems)"],
   ["What to give", "page", "the whole manual, or programs from a bigger model checked with answers", "fact", "one short fact: the model's own program that passed the check; no answers"],
   ["What it costs", "robot", "fine-tune a specialist (ORLM-8B): 69.5% on MAMO", "gpu", "untrained Qwen3-8B + that fact, one 24 GB GPU: the same 69.5%"]].forEach(([topic, li, lt, ri, rt], r) => {
    const y = 1.75 + r * 0.9;
    txt(s, topic, 0.6, y, 1.6, 0.75, { fontSize: 16, bold: true });
    box(s, "", 2.3, y, 4.6, 0.75, "F2F2F2");
    s.addImage({ path: ICON(li), x: 2.42, y: y + 0.15, w: 0.45, h: 0.45, objectName: "usual icon " + r });
    txt(s, lt, 3.0, y, 3.8, 0.75, { fontSize: 15, color: "404040" });
    s.addShape(pres.shapes.RIGHT_ARROW, { x: 7.0, y: y + 0.2, w: 0.5, h: 0.36, fill: { color: BLUE }, line: { color: BLUE }, objectName: "arrow " + r });
    box(s, "", 7.6, y, 5.1, 0.75, "DEEBF7");
    s.addImage({ path: ICON(ri), x: 7.72, y: y + 0.15, w: 0.45, h: 0.45, objectName: "ours icon " + r });
    txt(s, rt, 8.3, y, 4.3, 0.75, { fontSize: 15, bold: true, color: "1F3864" });
  });
  // next steps as a timeline
  txt(s, "Next, until the final report", 0.6, 4.5, 12.1, 0.4, { fontSize: 16, bold: true });
  s.addShape(pres.shapes.LINE, { x: 2.4, y: 5.25, w: 8.5, h: 0, line: { color: "BFBFBF", width: 3 } });
  [["check", "finish the held-out test on more models"], ["warn", "errors no check catches: programs that run but model the problem wrong"], ["code", "facts for every problem type; report and code"]].forEach(([icon, t], k) => {
    const x = 2.4 + k * 4.25;
    s.addShape(pres.shapes.OVAL, { x: x - 0.3, y: 4.95, w: 0.6, h: 0.6, fill: { color: "FFFFFF" }, line: { color: BLUE, width: 2 }, objectName: "milestone " + k });
    s.addImage({ path: ICON(icon), x: x - 0.19, y: 5.06, w: 0.38, h: 0.38, objectName: "milestone icon " + k });
    txt(s, t, x - 1.8, 5.58, 3.6, 0.55, { fontSize: 15, align: "center", valign: "top" });
  });
  caption(s, "Takeaway: give the missing fact first, and think only where a free check fails");

  // ---- extra pages that answer expected questions (each title is the question)
  function qSlide(title, sub) {
    s = pres.addSlide({ masterName: "Title Only", sectionTitle: "Extra pages" });
    s.addText(title, { placeholder: "title" });
    if (sub) txt(s, sub, 0.6, 1.3, 12.1, 0.45, { fontSize: 17 });
  }
  function slideQLeak() {
    qSlide("Q: what if a wrong program passes the check?", "It happens, but a perfect check would buy little: thinking rarely fixes those problems");
    [["24–37%", "of gpt-oss-120b's wrong contest programs pass the problem's examples"],
     ["12–16%", "of word problems: both programs agree and both are wrong (14B+ models)"]].forEach(([big, lab], k) => {
      const x = 0.6 + k * 4.1;
      panel(s, x, 1.95, 3.95, 1.9, "leak " + big);
      txt(s, big, x + 0.25, 2.05, 3.5, 0.75, { fontSize: 36, bold: true, color: RED });
      txt(s, lab, x + 0.25, 2.85, 3.5, 0.9, { fontSize: 15, valign: "top" });
    });
    panel(s, 8.8, 1.95, 3.9, 1.9, "example Find Color");
    txt(s, [{ text: "Example: \"Find Color\" (contest)", options: { bold: true, breakLine: true } }, { text: "passes all 3 examples → submitted", options: { breakLine: true } }, { text: "✗ fails hidden test 11", options: { bold: true, color: RED } }],
        9.05, 2.1, 3.45, 1.6, { fontSize: 15, valign: "top" });
    panel(s, 0.6, 4.1, 12.1, 1.85, "perfect check");
    txt(s, "If the check were perfect (word problems, every seed):", 0.85, 4.15, 11.6, 0.45, { fontSize: 16, bold: true });
    [["the leaked problems go to thinking", "FFFFFF"], ["thinking fixes only 7–16% of them", "FFFFFF"], ["+0.8 to +2.6 points (Qwen3-8B: +5.6)", "DEEBF7"]].forEach(([t, fill], k) => {
      const x = 0.85 + k * 3.0;
      box(s, t, x, 4.7, 2.6, 1.0, fill, { fontSize: 15, bold: k === 2, color: k === 2 ? "1F3864" : C.text1 });
      if (k < 2) arrow(s, x + 2.6, 5.2, x + 3.0, 5.2);
    });
    txt(s, "some 'wrong' answers are wrong labels: nl4opt-174 gold 7500, true 5625 (3 of 4 we read)", 9.85, 4.7, 2.7, 1.0, { fontSize: 14, color: C.text2 });
    caption(s, "Next target: programs that run and agree but model the problem wrong");
  }
  function slideQThink() {
    qSlide("Q: why can thinking make it worse?", "Qwen3-32B writes OR-Tools programs for optimization word problems (NL4OPT + IndustryOR)");
    [["thinking, no fact", "Objective().SetMaximize()", "✗ invented method: crash", "FCE4D6", RED, 1.95],
     ["exact usage first", "solver.Maximize(...)", "✓ the real call: runs", "E2F0D9", "38761D", 2.75]].forEach(([lab, call, res, fill, col, y]) => {
      box(s, lab, 0.6, y, 2.7, 0.6, fill, { fontSize: 16, bold: true });
      arrow(s, 3.3, y + 0.3, 3.65, y + 0.3);
      code(s, call, 3.65, y, 4.9, 0.6, col, 15);
      txt(s, res, 8.75, y, 3.9, 0.6, { fontSize: 17, bold: true, color: col });
    });
    txt(s, "% solved:", 0.6, 3.6, 12.1, 0.4, { fontSize: 17, bold: true });
    hbars(s, 0.6, 4.0, 12.1, [["no fact, no thinking", 65.4, "65.4%", "7F7F7F"], ["no fact, thinking", 52.0, "52.0%", RED],
                              ["fact, always thinking", 72.0, "72.0% · 5.5k tokens", "7F7F7F"], ["fact first, think on failure", 72.4, "72.4% · 1.3k tokens", BLUE]], 0.5, 3.4, 2.6);
    caption(s, "Thinking cannot add a fact the model lacks; given the fact first, thinking helps");
  }
  function slideQHard() {
    qSlide("Q: is 'think on the hardest' a weak baseline?", "We gave the router each problem's true Codeforces rating (exploratory; 311 contest problems, gpt-oss-120b, 3 seeds)");
    txt(s, "Send a problem to high effort when ...", 0.6, 1.9, 7.8, 0.4, { fontSize: 16, bold: true });
    costRows(0.6, 2.3, 7.8, 3.3, [["true rating ≥ 2600", "61.4%", 19.4, "19.4k", "7F7F7F"], ["true rating ≥ 2400", "63.3%", 22.7, "22.7k", "7F7F7F"],
      ["true rating ≥ 1800", "65.3%", 27.8, "27.8k", "7F7F7F"], ["its first answer is long", "62.1%", 23.0, "23.0k", "7F7F7F"],
      ["always", "66.2%", 30.1, "30.1k", "7F7F7F"], ["an example fails (free check)", "65.0%", 20.2, "20.2k", BLUE]]);
    [["74% → 87%", "208 geometry and optimization problems × 3 models: think on the hardest-looking (Snell et al.) → fact first, think on failure"],
     ["79%", "even with the best fix chosen per difficulty level"]].forEach(([big, lab], r) => {
      const y = 1.95 + r * 1.8;
      txt(s, big, 8.8, y, 3.9, 0.65, { fontSize: 32, bold: true, color: BLUE });
      txt(s, lab, 8.8, y + 0.7, 3.9, 0.9, { fontSize: 15, valign: "top" });
    });
    caption(s, "Even the true difficulty does not say which program is wrong; a free check does");
  }
  function slideQVote() {
    qSlide("Q: why not majority voting?");
    panel(s, 0.6, 1.35, 5.95, 4.65, "pick one of three");
    txt(s, "Pick 1 of 3 programs (Qwen3-8B, 300 geometry problems): % picked wrong", 0.85, 1.45, 5.5, 0.7, { fontSize: 16, bold: true, valign: "top" });
    hbars(s, 0.85, 2.25, 5.5, [["majority vote", 43, "4.3%", "7F7F7F"], ["CodeT (+340 tokens)", 40, "4.0%", "7F7F7F"], ["DeepConf", 53, "5.3%", "7F7F7F"],
                               ["MBR-exec", 63, "6.3%", "7F7F7F"], ["symmetry check", 3, "0.3%", BLUE]], 0.55, 2.2, 0.9);
    txt(s, "symmetry check: run the program on a moved copy; a right program gives the same answer (no extra tokens)", 0.85, 5.1, 5.5, 0.8, { fontSize: 14, color: C.text2, valign: "top" });
    panel(s, 6.75, 1.35, 5.95, 4.65, "votes vs checks");
    txt(s, "Qwen3-32B, word problems", 7.0, 1.45, 5.45, 0.4, { fontSize: 16, bold: true });
    costRows(7.0, 1.85, 5.45, 2.5, [["vote of 3 programs", "68.4%", 1.1, "1.1k", "7F7F7F"], ["vote of 3 thinking runs", "79.4%", 16.4, "16.4k", "7F7F7F"], ["fact first, think on failure", "72.4%", 1.3, "1.3k", BLUE]], 16.4);
    txt(s, "Voting three thinking runs is 7 points better here, but costs 12× the tokens of a free check.", 7.0, 4.25, 5.45, 0.9, { fontSize: 15, color: C.text2, valign: "top" });
    caption(s, "A check picks the right answer, a vote the popular one; 3 thinking runs win only at 12× tokens");
  }
  function slideQFair() {
    qSlide("Q: is the comparison fair?");
    [["coins", "Input tokens count too", "+213 tokens", "input tokens for the exact snippet (701 vs 488); a long reference sheet adds 413, extra tools 912. Input is cheaper and cacheable: no conclusion flips. Running programs uses CPU, which we do not count."],
     ["trophy", "Memorized problems?", "81% vs 83%", "older vs newer contests at the same difficulty (rating below 2000): no sign of memory, though all are before 2022. MAMO was held out until the end, and every method runs on the same model."],
     ["check", "Small differences", "3 seeds", "every claim pre-registered; when the gap is 1–4 problems we say 'same accuracy, fewer tokens', not 'better' (3 vs 1 problems: p = 0.62)."]].forEach(([icon, head, big, body], k) => {
      const x = 0.6 + k * 4.1;
      panel(s, x, 1.4, 3.9, 4.55, "fair " + head);
      s.addImage({ path: ICON(icon), x: x + 0.25, y: 1.6, w: 0.55, h: 0.55, objectName: "icon " + icon });
      txt(s, head, x + 0.95, 1.6, 2.8, 0.55, { fontSize: 18, bold: true });
      txt(s, big, x + 0.25, 2.35, 3.4, 0.75, { fontSize: 32, bold: true, color: BLUE });
      txt(s, body, x + 0.25, 3.2, 3.4, 2.6, { fontSize: 15, valign: "top" });
    });
    caption(s, "Same models, problems and grader for every method; every accuracy comes with its cost");
  }

  function slideQFact() {
    qSlide("Q: what exactly is the fact? Isn't it the answer?", "The fact for the routing problems of Finding 1: how to call OR-Tools (excerpt of the 11-line snippet)");
    s.addShape(pres.shapes.RECTANGLE, { x: 0.6, y: 1.95, w: 7.3, h: 3.95, fill: { color: "F7F7F7" }, line: { color: "BFBFBF", width: 0.75 }, objectName: "the fact, excerpt" });
    const L = (t, hot) => ({ text: t, options: { breakLine: true, bold: !!hot, color: hot ? "38761D" : C.text1 } });
    s.addText([L("mgr = pywrapcp.RoutingIndexManager(n + 1, K, 0)"), L("r = pywrapcp.RoutingModel(mgr)"), L("cb = r.RegisterTransitCallback(cost)"),
               L("r.SetArcCostEvaluatorOfAllVehicles(cb)"), L("dcb = r.RegisterUnaryTransitCallback(demand)", 1),
               L("r.AddDimensionWithVehicleCapacity(dcb, 0, [Q] * K,", 1), L("                 True, \"Load\")", 1),
               L("p.first_solution_strategy = ...PATH_CHEAPEST_ARC"), L("sol = r.SolveWithParameters(p)"), { text: "...  (11 lines in all)", options: { color: "7F7F7F" } }],
      { isTextBox: true, x: 0.8, y: 2.05, w: 7.0, h: 3.75, fontFace: "Courier New", fontSize: 14, valign: "middle", margin: 0 });
    [["✓", "how to call the library: names and arguments", "38761D"], ["✓", "the same text for all 30 problems of this kind", "38761D"], ["✗", "no route, no numbers, no answer", RED]].forEach(([m, t, col], r) => {
      txt(s, m, 8.2, 1.95 + r * 0.55, 0.35, 0.5, { fontSize: 18, bold: true, color: col });
      txt(s, t, 8.55, 1.95 + r * 0.55, 4.15, 0.5, { fontSize: 15 });
    });
    panel(s, 8.2, 3.75, 4.5, 2.15, "why the sheet hurts");
    txt(s, [{ text: "Why is a long reference sheet worse than nothing (7% vs 23%)?", options: { bold: true, breakLine: true } },
            { text: "It shows routing, but not the capacity rule. The model fills the gap with a call that does not exist (10 programs: RegisterUnaryLongLivingCallback)." }],
        8.4, 3.85, 4.1, 1.95, { fontSize: 14, valign: "top" });
    caption(s, "The fact says how to call the library, not how to solve the problem");
  }
  function slideQRag() {
    qSlide("Q: can retrieval (RAG) find the fact?", "BM25 search over a library of titled snippets, Qwen3-32B, % solved optimally (seed 1)");
    [["6 optimization problems", [["no fact", 67, "67%", "7F7F7F"], ["hand-written fact", 96, "96%", "7F7F7F"], ["retrieved, top 1", 97, "97%", BLUE], ["retrieved, top 3", 93, "93%", BLUE], ["untitled pages, top 3", 90, "90%", "7F7F7F"]]],
     ["Routing (30 CVRP problems)", [["no fact", 23, "23%", "7F7F7F"], ["hand-written fact", 83, "83%", "7F7F7F"], ["retrieved, top 1", 70, "70%", BLUE], ["top 3 (+ a near miss)", 57, "57%", RED], ["untitled pages, top 3", 53, "53%", "7F7F7F"]]]].forEach(([head, rows], k) => {
      const x = 0.6 + k * 6.15;
      panel(s, x, 1.9, 5.95, 3.7, "rag " + head);
      txt(s, head, x + 0.25, 2.0, 5.45, 0.45, { fontSize: 18, bold: true, color: BLUE });
      hbars(s, x + 0.25, 2.55, 5.5, rows, 0.58, 2.3, 0.75);
    });
    txt(s, `The near miss: top 3 also brings the TSP routing page. No documentation at all? The model's own checked program is the fact (page ${page("auto")}).`, 0.6, 5.65, 12.1, 0.5, { fontSize: 15, color: C.text2 });
    caption(s, "Precise retrieval works like a hand-written fact; a near-miss page can cost 26 points");
  }
  function slideQChecks() {
    qSlide("Q: is there always a free check?");
    table(s, [[HDR("Problem"), HDR("Free check (no answer key)"), HDR("How well it works")],
      ["Contest problems", "the examples printed in the problem; a quick brute-force program must agree", "examples never reject a right program, but 24–37% of wrong ones pass; with brute force: 66.3% = always thinking"],
      ["Geometry", "move or turn the input: the answer must not change; or two versions must agree", "picks the right program 99.7% of the time (majority vote: 95.7%)"],
      ["Routing, scheduling", "code checks every rule of the plan (capacity, time windows)", "exact for the rules; whether the plan is the best is not checked"],
      ["Word problems", "two programs must agree", "12–16% agree but are both wrong"],
],
      { x: 0.6, y: 1.45, w: 12.1, colW: [2.4, 5.0, 4.7], fontSize: 15, rowH: 0.8 });
    caption(s, "Every task here has a free check; how much it catches decides how much thinking it saves");
  }

  function slideQCoverage() {
    qSlide("Q: do the findings cover every kind?", "Where each result was measured (models and numbers as on the talk slides)");
    const OK = "38761D", PART = "C55A11", NA = "8C8C8C";
    const c = (t, col) => ({ text: t, options: { color: col } }), row = t => ({ text: t, options: { bold: true } });
    table(s, [["", "Geometry", "Contest problems", "Routing, scheduling", "Word problems"].map(HDR),
      [row("Give the fact"), c("✓ only the needed tools: 92% vs 75%", OK), c("✗ no library to hint; 8 geometry helpers hurt: 37.7% → 33.4% (gpt-oss-20b)", RED), c("✓ 23% → 77–90%; 6% → 100% valid plans", OK), c("✓ 65% → 72%; small models +44 points", OK)],
      [row("Free check, think on failure"), c("✓ 99% @ 4.3k vs 98% @ 5.9k", OK), c("✓ 66.3% @ 24.7k vs 66.2% @ 30.1k (examples + brute force)", OK), c("✓ part of the 87% below", OK), c("✓ beats always thinking at 12–22% of its tokens", OK)],
      [row("Whole recipe"), c("✓ 87% @ 2.5k vs 74% @ 4.1k, with routing", OK), c("~ steps 3–4 only (no library, so no hint): same 66% at 18% fewer tokens", PART), c("✓ 87% @ 2.5k vs 74% @ 4.1k, with geometry", OK), c("✓ held-out MAMO: automatic fact = hand-written", OK)],
      [row("Reuse a checked program"), c("– not tested", NA), c("– each problem is new", NA), c("✓ 94% vs 7% of days valid", OK), c("– not tested", NA)]],
      { x: 0.6, y: 1.85, w: 12.1, colW: [2.5, 2.4, 2.4, 2.4, 2.4], fontSize: 14, rowH: [0.45, 0.85, 0.85, 0.85, 0.6] });
    txt(s, "✓ holds   ~ partly   ✗ does not help   – not tested.   The 87% pools 108 geometry and 100 optimization problems, each solved by 3 models.", 0.6, 5.75, 12.1, 0.4, { fontSize: 14, color: C.text2 });
    caption(s, "Contest problems need no library, so no hint: the check and thinking alone, at 18% fewer tokens");
  }

  function slideQWhy() {
    qSlide("Q: why these problems, and how do they differ?", "Exact answers that code can grade, a free check for each, and code that agents already write");
    const fam = (t, col) => ({ text: t, options: { colspan: 2, bold: true, color: "FFFFFF", fill: { color: col }, align: "center" } });
    const lab = t => ({ text: t, options: { bold: true } });
    table(s, [[{ text: "", options: { fill: { color: "FFFFFF" } } }, fam("needs the right algorithm", BLUE), fam("needs the right solver call", "38761D")],
      ["", "Geometry", "Contest problems", "Routing, scheduling", "Word problems"].map(HDR),
      [lab("Input"), "points, polygons", "a story with an input format", "data: customers, loads, time windows", "a paragraph of text"],
      [lab("The program"), "a textbook algorithm in plain Python", "a harder algorithm (Codeforces Master level)", "a call to a solver library (OR-Tools)", "text → equations, then a solver call"],
      [lab("Free check"), "move or turn the input; two versions", "the examples; a brute-force program", "code checks every rule of the plan", "two programs must agree"],
      [lab("Typical failure"), "a wrong method, steered by offered tools", "wrong reasoning", "an invented library name", "an invented name, or a wrong model of the text"],
      [lab("What helps most"), "a free check, then think", "think only when the check fails", "the exact usage; reuse", "the fact, then the check"],
      [lab("Size"), "108 problems (9 tasks)", "311 problems", "100 (8 types) + 56 Solomon + 82 job-shop", "1,208 (NL4OPT, IndustryOR, MAMO)"]],
      { x: 0.6, y: 1.85, w: 12.1, colW: [2.1, 2.5, 2.5, 2.5, 2.5], fontSize: 13, rowH: 0.48 });
    caption(s, "Two needs, an algorithm or a library fact, so we can see where extra effort pays");
  }

  function slideQHowHint() {
    qSlide("Q: how do we get the exact hint?", "One hint per problem type, put in the prompt before the task; it shows only the calls that type needs");
    [["pen", "Written by hand", "once per problem type: the exact library usage (e.g. 11 lines for truck routing)", "routing 23% → 77–90%; word problems 65% → 72% (Qwen3-32B)", "needs someone who knows the library"],
     ["shapes", "Found by search", "BM25 over a small library of titled usage snippets; take the top one", "97% vs 96% by hand (6 optimization problems); 84% vs 87% on the 208-problem suite", "a near-miss page hurts: routing 83% → 57%"],
     ["check", "Taken from the model's own work", "run the model on other problems of the same type; keep programs that pass the free check; use the shortest", "held-out MAMO (863), automatic vs by hand: 79% = 79% (gpt-oss-20b), 72% vs 71% (Qwen3-14B), 71% vs 72% (Qwen3-8B)", "only within one problem type: another type's program costs 14–21 points"]].forEach(([icon, head, how, res, lim], k) => {
      const x = 0.6 + k * 4.1;
      panel(s, x, 1.9, 3.9, 4.15, "how hint " + head);
      s.addImage({ path: ICON(icon), x: x + 0.2, y: 2.02, w: 0.45, h: 0.45, objectName: "icon " + icon });
      txt(s, head, x + 0.75, 2.0, 3.0, 0.5, { fontSize: 17, bold: true, color: BLUE });
      txt(s, [{ text: "How: ", options: { bold: true } }, { text: how }], x + 0.2, 2.6, 3.5, 1.15, { fontSize: 14, valign: "top" });
      txt(s, [{ text: "Result: ", options: { bold: true } }, { text: res }], x + 0.2, 3.8, 3.5, 1.15, { fontSize: 14, valign: "top", color: "38761D" });
      txt(s, [{ text: "Limit: ", options: { bold: true } }, { text: lim }], x + 0.2, 5.0, 3.5, 0.95, { fontSize: 14, valign: "top", color: RED });
    });
    caption(s, "Only the needed calls: with all helpers 75%, with only the needed ones 92% (geometry)");
  }

  const EXTRAS = [   // [key, index label, slide], in the order of the talk slides that raise the questions
    ["why", "Why these problems", slideQWhy],
    ["coverage", "Which kinds each finding covers", slideQCoverage],
    ["kinds", "How hard: contest ranks, exams", () => slideKinds("Extra pages", "Extra: how hard, by contest ranks and exams")],
    ["two", "Two versions, in detail", () => slideTwoVersions("Extra pages", "Extra: two versions catch each other's mistakes")],
    ["fact", "What the fact is", slideQFact],
    ["howhint", "How we get the hint", slideQHowHint],
    ["rag", "Can retrieval find the fact?", slideQRag],
    ["think", "Why thinking can hurt", slideQThink],
    ["leak", "A wrong program passes the check", slideQLeak],
    ["checks", "A free check for every problem", slideQChecks],
    ["auto", "Facts without a human", () => slideAuto("Extra pages", "Extra: the fact can be found without a human")],
    ["hard", "Is difficulty the right signal?", slideQHard],
    ["published", "Compared with published methods", () => slideBaselines("Extra pages", "Extra: compared with published methods")],
    ["related", "Related research map", () => slideRelated("Extra pages", "Extra: where this work sits in related research")],
    ["reported", "Numbers reported in papers", () => slideReported("Extra pages", "Extra: numbers reported in papers, next to ours")],
    ["vote", "Why not majority voting?", slideQVote],
    ["fair", "Is the comparison fair?", slideQFair],
    ["small", "One fact helps small models most", () => slideSmall("Extra pages", "Extra: one fact helps small models most")],
    ["policies", "All policies, cost vs accuracy", () => slideTogether("Extra pages", "Extra: all policies, cost vs accuracy")],
    ["limits", "Where the recipe stops", () => slideLimits("Extra pages", "Extra: where the recipe stops, and what is next")],
    ["reuse", "Reuse a checked program", () => slideReuse("Extra pages", "Extra: repeated problems need one checked program")],
    ["setup", "Setup", () => slideSetup("Extra pages", "Extra: setup, scoring and hardware")],
  ];
  const QUESTIONS = [   // [talk slide that raises it, expected question, extra pages that answer it]
    [2, "Why these problems? How do they differ?", ["why"]],
    [2, "Do the findings cover every kind?", ["coverage"]],
    [2, "How hard are the problems?", ["kinds"]],
    [4, "Why does helper code change the answer?", ["two"]],
    [5, "What exactly is the fact? Isn't it the answer?", ["fact"]],
    [5, "How do we get the exact hint?", ["howhint", "auto"]],
    [5, "Can retrieval (RAG) find the fact?", ["rag"]],
    [5, "Why can thinking make it worse?", ["think"]],
    [6, "What if a wrong program passes the check?", ["leak"]],
    [6, "Is there always a free check?", ["checks"]],
    [7, "Who writes the fact?", ["auto"]],
    [7, "Is 'think on the hardest' a weak baseline?", ["hard"]],
    [7, "What if the same problem repeats?", ["reuse"]],
    [7, "Why no hint for contest problems?", ["coverage"]],
    [7, "Where does the recipe stop?", ["limits"]],
    [8, "What is new vs PAL and cascades?", ["published", "related", "reported"]],
    [8, "Why not majority voting?", ["vote"]],
    [8, "Is the comparison fair?", ["fair", "setup"]],
    [8, "Does it hold for smaller models?", ["small"]],
  ];
  s = pres.addSlide({ masterName: "Title Slide", sectionTitle: "Talk" });
  s.addText("Thank you", { placeholder: "title" });
  s.addText([{ text: "Questions?", options: { breakLine: true } }, { text: "Team 5: Sangjun Lee, Seongbin Park", options: { fontSize: 16, color: THEME.colors.dk2 } }], { placeholder: "body" });
  // the expected questions and their extra pages go to this slide's notes, for the presenters
  const first = pres.slides.length + 1, page = key => first + EXTRAS.findIndex(e => e[0] === key);
  const qaIndex = QUESTIONS.map(([from, q, keys]) => `${keys.map(page).sort((x, y) => x - y).join(", ")}: ${term(q)} (slide ${from})`).join("\n");
  SCRIPT_KO.forEach((t, i) => pres.slides[i].say(i === 8 ? t + "\n\n[발표자용] 예상 질문 → 보충 슬라이드 번호 (슬라이드 쇼에서 번호를 누르고 Enter):\n" + qaIndex : t));

  pres.addSection({ title: "Extra pages" });
  EXTRAS.forEach(([key, , make]) => { make(); s.say(QA_KO[key]); });

  pres.writeFile({ fileName: OUT }).then(async () => { await applyTheme(OUT, THEME); console.log("written", OUT); });
}
