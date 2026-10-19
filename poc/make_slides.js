// Proposal deck in the default Office look (white, Calibri Light / Calibri, Office accent colours).
const pptxgen = require("pptxgenjs");
const path = require("path");
// optional: writes the theme colours into the deck (from the pptx skill); without it the deck keeps the default Office theme
let applyTheme = async () => {};
try { ({ applyTheme } = require(process.env.PPTX_THEME_JS || "/root/.claude/skills/synced/3c05885e-4c45-4ba8-8aac-398768cdc097_763b3f05-13a5-417f-9a5f-72964acfee24/pptx/scripts/apply_theme.js")); } catch (e) {}

const ROOT = process.env.PROJECT_ROOT || path.join(__dirname, "..");   // repository root (this file is poc/make_slides.js)
const FIG = (f) => path.join(ROOT, "figs", f);
const OUT = path.join(ROOT, "PROPOSAL_slides.pptx");

const THEME = {
  name: "Office Theme", headFontFace: "Calibri", bodyFontFace: "Calibri",
  colors: { dk1: "000000", lt1: "FFFFFF", dk2: "44546A", lt2: "E7E6E6", accent1: "4472C4", accent2: "ED7D31", accent3: "A5A5A5",
            accent4: "FFC000", accent5: "5B9BD5", accent6: "70AD47", hlink: "0563C1", folHlink: "954F72" },
};

const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE"; // 13.333 x 7.5, the PowerPoint default
pres.theme = { headFontFace: THEME.headFontFace, bodyFontFace: THEME.bodyFontFace };
pres.title = "Solving Computational Math with LLMs, Accurately and Cheaply";
pres.author = "POSTECH graduate NLP course project";
const C = pres.SchemeColor;

// ---- layouts modelled on the default template ----
pres.defineSlideMaster({
  title: "Title Slide", background: { color: "FFFFFF" },
  objects: [
    { placeholder: { options: { name: "title", type: "title", x: 1.67, y: 1.4, w: 10.0, h: 2.4, fontSize: 54, align: "center", valign: "bottom", color: C.text1 }, text: "" } },
    { placeholder: { options: { name: "body", type: "body", x: 1.67, y: 4.0, w: 10.0, h: 1.7, fontSize: 22, align: "center", valign: "top", color: C.text1 }, text: "" } },
  ],
});
pres.defineSlideMaster({
  title: "Title Only", background: { color: "FFFFFF" },
  slideNumber: { x: 12.2, y: 6.95, w: 0.8, h: 0.35, fontSize: 12, color: "8C8C8C", align: "right" },
  objects: [
    { placeholder: { options: { name: "title", type: "title", x: 0.6, y: 0.3, w: 12.1, h: 1.0, fontSize: 36, align: "left", valign: "middle", color: C.text1 }, text: "" } },
  ],
});
pres.defineSlideMaster({
  title: "Title and Content", background: { color: "FFFFFF" },
  slideNumber: { x: 12.2, y: 6.95, w: 0.8, h: 0.35, fontSize: 12, color: "8C8C8C", align: "right" },
  objects: [
    { placeholder: { options: { name: "title", type: "title", x: 0.6, y: 0.3, w: 12.1, h: 1.0, fontSize: 36, align: "left", valign: "middle", color: C.text1 }, text: "" } },
    { placeholder: { options: { name: "body", type: "body", x: 0.6, y: 1.5, w: 12.1, h: 5.3, fontSize: 18, valign: "top", color: C.text1 }, text: "" } },
  ],
});

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
pres.addSection({ title: "Problem" });
let s = pres.addSlide({ masterName: "Title Slide", sectionTitle: "Problem" });
s.addText([{ text: "Solving Computational Math", options: { fontSize: 44, breakLine: true } },
            { text: "with LLMs, Accurately and Cheaply", options: { fontSize: 40 } }], { placeholder: "title" });
s.addText([
  { text: "Tools, Facts, and Checks", options: { breakLine: true } },
  { text: "POSTECH CSED490E (Graduate NLP) · Team 5 · October 2026", options: { fontSize: 16, color: THEME.colors.dk2 } },
], { placeholder: "body" });
s.addNotes("Computational math: geometry, optimization, contest problems, word problems whose answer must be computed exactly. We ask how to get them right with the fewest tokens and the smallest GPU.");

// 2. Problem
s = pres.addSlide({ masterName: "Title Only", sectionTitle: "Problem" });
s.addText("Let the computer do the math", { placeholder: "title" });
s.addText("Same shape moved, turned or flipped, so the right answer never changes: 436 (twice its area)",
  { isTextBox: true, x: 3.9, y: 1.35, w: 8.8, h: 0.45, fontSize: 16, color: C.text1, align: "center", margin: 0 });
s.addImage({ path: FIG("slide2_shapes.png"), x: 3.9, y: 1.85, w: 8.8, h: 1.9, objectName: "four copies of one polygon", altText: "one polygon: original, moved, turned, flipped" });
["original", "moved", "turned", "flipped"].forEach((t, k) => {
  s.addText(t, { isTextBox: true, x: 3.9 + k * 2.2, y: 3.55, w: 2.2, h: 0.35, fontSize: 16, color: C.text2, align: "center", margin: 0 });
});
[["Answer in words", "the model does the arithmetic itself", [["436 ✓", 1], ["2944 ✗", 0], ["392 ✗", 0], ["728 ✗", 0]], 4.3],
 ["Write a program", "the computer does the arithmetic", [["436 ✓", 1], ["436 ✓", 1], ["436 ✓", 1], ["436 ✓", 1]], 5.15]].forEach(([head, sub, ans, y]) => {
  s.addText([{ text: head, options: { bold: true, fontSize: 20, breakLine: true } }, { text: sub, options: { fontSize: 14, color: THEME.colors.dk2 } }],
    { isTextBox: true, x: 0.6, y: y - 0.1, w: 3.2, h: 0.8, valign: "middle", margin: 0, color: C.text1 });
  ans.forEach(([t, ok], k) => chip(s, t, ok, 3.9 + k * 2.2, y));
});
caption(s, "But programs can be silently wrong, and thinking is expensive. Goal: right answers, lowest cost.");
s.addNotes("Qwen3-8B, real outputs. Asked to answer directly, it gives a different area for each copy of the same polygon (only the original is right). Asked for a program, it writes the shoelace formula and the computer gets all copies right. Programs still fail silently, and thinking longer is expensive: on 311 contest problems gpt-oss-120b goes from 57% to 66% for 4.4 times the tokens. Goal: effective (exactly right) and efficient (fewest tokens, smallest GPU).");

// 3. Words
s = pres.addSlide({ masterName: "Title Only", sectionTitle: "Problem" });
s.addText("Words we use", { placeholder: "title" });
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
s.addNotes("Plain definitions for the rest of the talk. Every result is reported as accuracy and tokens (cost).");

pres.addSection({ title: "Findings" });
// 4b. Results at a glance
s = pres.addSlide({ masterName: "Title Only", sectionTitle: "Findings" });
s.addText("Findings at a glance: same or better, for fewer tokens", { placeholder: "title" });
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
s.addNotes("One panel per result. Add the fact: routing 23% to 77-90% (thinking longer 3%, whole manual 7%). Small models gain most: Qwen3-1.7B 0% to 45%, Qwen3-32B 65% to 66% (word problems). Compare two versions: 99% at 4.3k tokens vs always thinking 98% at 5.9k; with 8 extra tools 59%. Think only on a failed check (gpt-oss-120b, contest): 66.3% at 24.7k vs 66.2% at 30.1k. Reuse: 94% of 48 routing days vs 7% with a new program per day; Dynamic Cheatsheet (DC, the model's own notes) 31-40%. All together: fact first then think on failure 87% at 2.5k vs 74% at 4.1k for thinking on the hardest-looking problems (Snell-style) and 83% for choosing the fix by failure type.");

// 5. Step 2: fact
// 4. Missing knowledge
s = pres.addSlide({ masterName: "Title Only", sectionTitle: "Findings" });
s.addText("Finding 1: give the fact, not the manual", { placeholder: "title" });
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
s.addNotes("The model writes the program (the right side shows the line that matters). With a long reference sheet it guesses a plausible function name that does not exist and crashes; with five lines showing the exact call it writes the right one. Thinking longer cannot supply a fact it does not have (3 of 100). On the 56 standard Solomon routing problems, three such facts together take gpt-oss-120b to a valid plan on every instance.");

// 5b. Small models
s = pres.addSlide({ masterName: "Title Only", sectionTitle: "Findings" });
s.addText("Finding 2: one fact helps small models most", { placeholder: "title" });
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
s.addNotes("SIZE study. Without the snippet the 1.7B model invents OR-Tools attributes and almost never runs (0.1%); with six lines of exact usage it solves 44.5%. The gain shrinks as the model grows (+44, +31, +17, +8, +1 points). With the recipe (fact first, think only when the check fails), models that fit one 24 GB GPU match or beat Qwen3-32B: gpt-oss-20b 73.0% at 0.7k tokens vs Qwen3-32B with the fact and always thinking 72.0% at 5.5k; on the optimization suite Qwen3-14B (4-bit) 87-92% vs Qwen3-32B 79-85%. Below 14B the optimization suite stays at 47% or less.");

// 5. Steering
s = pres.addSlide({ masterName: "Title Only", sectionTitle: "Findings" });
s.addText("Finding 3: two versions catch each other's mistakes", { placeholder: "title" });
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
s.addNotes("The example (Qwen3-14B, real output): the only difference between the two prompts is the toolbox, eight correct helper functions that the task does not need. We run the two finished programs ourselves. Program A prints 6, the right answer; program B builds its method on polar_sort and prints 0. The bars (Qwen3-32B, 108 generated geometry problems, mean of 3 runs; tokens = output tokens per problem, both cheap programs counted for the last row): with the helpers 59%, task only 77%, always thinking 98% at 5.9k tokens, and writing both cheap programs and thinking only when their answers differ 99% at 4.3k (27% fewer tokens; the pair differs on 37-53% of problems). It does not help when both programs share the mistake (gpt-oss-120b on contest problems).");

// 6. Hard problems
s = pres.addSlide({ masterName: "Title Only", sectionTitle: "Findings" });
s.addText("Finding 4: think harder only when a check fails", { placeholder: "title" });
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
s.addNotes("Real gpt-oss-120b runs on Codeforces geometry problems. The examples are a free check: if the quick (medium-effort) program gets them right we submit it; if not, we pay for high effort. Examples can miss bugs (Find Color passed all 3 examples and failed hidden test 11), so the full policy also runs a quick brute-force comparison on small inputs. Result: 66.3% at 24.7k tokens per problem vs 66.2% at 30.1k for always high effort.");

// 7. Pay once
s = pres.addSlide({ masterName: "Title Only", sectionTitle: "Findings" });
s.addText("Finding 5: repeated problems need one checked program", { placeholder: "title" });
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
s.addNotes("Analogy for the 56 Solomon routing problems: each problem is like one day's orders. A: a new program per day is valid on 6 and 1 of 48 days in two runs (7%; drawn as 3), about 1.8k tokens each. B: draw 16 programs once, keep the one that gives valid plans on 8 practice days, reuse it: valid on 45 of 48 days (94%), 28k tokens in total. Reused programs also work on 200- and 400-customer problems; for a new rule (job-shop with release dates) editing the working program beats writing a new one (10% to 68-100%).");

// 7b. Finding 6: automatic facts
s = pres.addSlide({ masterName: "Title Only", sectionTitle: "Findings" });
s.addText("Finding 6: the fact can be found without a human", { placeholder: "title" });
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
s.addNotes("Real outputs, Qwen3-8B on MAMO easy-189 (gold 20000). Without a fact it writes solver.Objective().Minimize() and crashes (AttributeError). The fact is chosen automatically: its own shortest program from NL4OPT (a vans-and-trucks problem) that passed the label-free check (it runs and prints a value); no answers, no human. With it, both programs write solver.Minimize(10*x + 15*y + 20*z) and print 20000 (316 + 312 tokens), they agree, so no thinking is needed (thinking alone: 5,323 tokens). Chart: on the held-out MAMO the automatic fact matches the hand-written one (gpt-oss-20b within 1.2 points on 3 seeds). It stays within a problem family: a program of another problem type is 14-21 points below the hand-written fact on the optimization suite, and an introspected list of names hurts (Qwen3-32B 66.2 to 56.1%).");

// 7c. Finding 7: proofs
s = pres.addSlide({ masterName: "Title Only", sectionTitle: "Findings" });
s.addText("Finding 7: proofs need a specialized model, not a fact", { placeholder: "title" });
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
s.addNotes("Real outputs. miniF2F mathd_numbertheory_34 (9^-1 mod 100 = 89). Qwen3-32B's 8 attempts all fail; they cite lemmas that do not exist, e.g. Nat.ModEq_iff_modEq. Goedel-Prover-V2-8B proves it by checking every x below 100 (interval_cases, then norm_num and omega). Specialized provers rarely invent names (6-7% of failed attempts vs 22-40%). For general models a verified proof of the most similar statement, thinking, or an inequality toolkit does not help; even for provers, revising from Lean's errors proves half as many as a fresh attempt (Goedel 11 vs 22 of 107). Geometry: AlphaGeometry's DD+AR engine alone proves 12 of IMO-AG-30 and 187 of JGEX-AG-231; LLM auxiliary points add 13 JGEX problems and only IMO 2014 P4 (d = midpoint of b c).");

pres.addSection({ title: "Method" });
// 4. Recipe
s = pres.addSlide({ masterName: "Title Only", sectionTitle: "Method" });
s.addText("Our method: a recipe built from the findings", { placeholder: "title" });
function step(s, n, head, res, x, y, w) {
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w, h: 1.35, rectRadius: 0.08, fill: { color: "DEEBF7" }, line: { color: "BDD7EE", width: 0.75 }, objectName: "step " + n });
  s.addShape(pres.shapes.OVAL, { x: x + 0.15, y: y + 0.3, w: 0.7, h: 0.7, fill: { color: BLUE }, line: { color: BLUE }, objectName: "badge " + n });
  s.addText(String(n), { isTextBox: true, x: x + 0.15, y: y + 0.3, w: 0.7, h: 0.7, fontSize: 24, bold: true, color: "FFFFFF", align: "center", valign: "middle", margin: 0 });
  txt(s, head, x + 0.95, y + 0.1, w - 1.05, 1.15, { fontSize: 18, bold: true });
  txt(s, res, x, y + 1.42, w, 0.75, { fontSize: 14, color: C.text2, align: "center", valign: "top" });
}
step(s, 1, "Write a program", "right on 8 of 8 copies (slide 2)", 0.6, 1.7, 2.9);
arrow(s, 3.5, 2.37, 3.9, 2.37);
step(s, 2, "Add the missing fact", "23% → 77–90%; can be automatic (findings 1, 2, 6)", 3.9, 1.7, 3.0);
arrow(s, 6.9, 2.37, 7.3, 2.37);
step(s, 3, "Run a free check", "examples, or two versions agree (finding 3)", 7.3, 1.7, 2.9);
arrow(s, 10.2, 2.1, 10.6, 1.85); arrow(s, 10.2, 2.65, 10.6, 2.95);
box(s, "pass → done", 10.6, 1.55, 2.1, 0.6, "E2F0D9", { fontSize: 16, bold: true });
box(s, "fail → 4. think harder", 10.6, 2.65, 2.1, 0.75, "FADBD8", { fontSize: 16, bold: true });
txt(s, "same 66%, 18% fewer tokens (finding 4)", 10.4, 3.45, 2.5, 0.6, { fontSize: 14, color: C.text2, align: "center", valign: "top" });
step(s, 5, "Same problem again? Reuse the checked program", "valid plans 7% → 94% (finding 5)", 3.9, 4.3, 6.3);
caption(s, "Together: 87% solved at 2.5k tokens, vs 74% at 4.1k for \"think longer on hard problems\"");
s.addNotes("Each step is a measured result, shown on the next slides with an example. Step 1: the polygon. Step 2: delivery routing with OR-Tools (Qwen3-32B). Step 3: free checks (the problem's examples; two versions that should agree). Step 4: contest geometry with gpt-oss-120b. Step 5: reuse on the Solomon routing benchmark. Together (3 models, 624 geometry and optimization problems, 3 seeds): fact first and thinking only on a failed check solves 87% at 2.5k tokens per problem.");

// 9. All together
s = pres.addSlide({ masterName: "Title Only", sectionTitle: "Method" });
s.addText("All together: facts first, think only on failure", { placeholder: "title" });
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
s.addNotes("Right panel (MODEL, 63 model x task x seed cells; 0.5 points per 1k tokens): fact first, think on failure is the best fixed default (1.4 points from each cell's best policy; always thinking 8.4); choosing among 4 policies on 30 labelled problems of the new task cuts it to 0.6 (MAMO: 0.8-1.4). U1 / U1r / U2 (pre-registered). Qwen3-8B, Qwen3-32B and Qwen3.6 on the generated geometry and optimization suites, 624 problems, cure seed 1 shown; the order is the same on seeds 2 and 3. Thinking on the hardest-looking problems (difficulty-based allocation, as in compute-optimal scaling work) is even below thinking whenever the check fails. Giving the fact first and thinking only when the check fails is the most accurate and uses fewer tokens than any thinking policy; with automatically retrieved facts (BM25) it still reaches 84%.");

// 9b. Published methods
s = pres.addSlide({ masterName: "Title Only", sectionTitle: "Method" });
s.addText("Compared with published methods", { placeholder: "title" });
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
  ];
  table(s, rows, { x: 0.6, y: 1.45, w: 12.1, colW: [2.3, 3.9, 2.2, 3.7], rowH: 0.62, fontSize: 15 });
}
caption(s, "Measured here with the same problems and models: the recipe is more accurate, cheaper, or both");
s.addNotes("All baselines were run by us on our benchmarks. Models: U1 policies over Qwen3-8B / Qwen3-32B / Qwen3.6 (624 problems); contest geometry gpt-oss-120b (311); selection Qwen3-8B (300 geometry instances, 3 candidates); documentation Qwen3-32B on CVRP; tools Qwen3-32B on 5 geometry tasks; daily routing gpt-oss-120b on 48 held-out Solomon instances. Tokens are output tokens per problem. More rows (MBR-exec, majority vote, DeepConf, Self-Debugging, Mixture-of-Thought cascade, BM25 retrieval) are in PROPOSAL.md section 7.");

// 10. Limits and next
pres.addSection({ title: "Next" });
s = pres.addSlide({ masterName: "Title Only", sectionTitle: "Next" });
s.addText("Where the recipe stops, and what is next", { placeholder: "title" });
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
s.addNotes("Updated 2026-10-19. Done since the last version: contest geometry and competition math on 24 GB GPUs, Qwen3.6 with the model card settings (headline unchanged), automatic facts and the held-out MAMO test, the policy model, proofs. Older notes: for Lean proofs an invented lemma stands for a missing proof step (similar-name feedback fixes 2.7%, a fresh try 3.2%); for PopQA thinking adds 1.8-5 points at 70-200 times the tokens, only for well-known facts. Checks leak, which caps every policy. Facts were hand-written; BM25 retrieval recovers most of the gain. Next: SIZE-CC (gpt-oss-20b on contest geometry with check-gated escalation), X1-SIZE (competition math for Qwen3-4B/8B/14B), automatic facts, a closed API model, final report.");

pres.writeFile({ fileName: OUT }).then(async () => { await applyTheme(OUT, THEME); console.log("written", OUT); });
