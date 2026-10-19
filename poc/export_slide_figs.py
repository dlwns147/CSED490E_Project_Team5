"""Export example slides of the full deck PROPOSAL_slides_full.pptx as figures for PROPOSAL.md (figs/ex_*.png): slide -> PDF (LibreOffice)
-> PNG at 150 dpi (pdftoppm), cropped to the content (slide title and footer removed). Slides are found by their title, so reordering the
deck does not break the export.
usage: python poc/export_slide_figs.py   (needs soffice, pdftoppm and pdftotext; rebuild the deck first with node poc/make_slides.js)"""
import os, shutil, subprocess, sys, tempfile
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIGS = {"Finding 1:": "ex_finding1", "Finding 2:": "ex_finding2", "Finding 3:": "ex_finding3", "Finding 4:": "ex_finding4",
        "Finding 5:": "ex_finding5", "Finding 6:": "ex_finding6", "Finding 7:": "ex_finding7", "Our method on one real problem": "ex_method",
        "The problems we study": "ex_problems"}

with tempfile.TemporaryDirectory() as d:
    shutil.copy(os.path.join(ROOT, "PROPOSAL_slides_full.pptx"), d)
    subprocess.run(["soffice", "--headless", "--convert-to", "pdf", "--outdir", d, os.path.join(d, "PROPOSAL_slides_full.pptx")], check=True,
                   stdout=subprocess.DEVNULL)
    pdf = os.path.join(d, "PROPOSAL_slides_full.pdf")
    pages = int(next(l for l in subprocess.run(["pdfinfo", pdf], capture_output=True, text=True).stdout.splitlines() if l.startswith("Pages:")).split()[1])
    for n in range(1, pages + 1):
        first = subprocess.run(["pdftotext", "-f", str(n), "-l", str(n), pdf, "-"], capture_output=True, text=True).stdout.strip()
        name = next((v for k, v in FIGS.items() if first.startswith(k)), None)
        if not name:
            continue
        subprocess.run(["pdftoppm", "-png", "-r", "150", "-f", str(n), "-l", str(n), "-singlefile", pdf, os.path.join(d, name)], check=True)
        im = Image.open(os.path.join(d, name + ".png")).convert("RGB")
        w, h = im.size
        im.crop((0, int(h * 1.22 / 7.5), w, int(h * 6.85 / 7.5))).save(os.path.join(ROOT, "figs", name + ".png"), optimize=True)
        print(f"slide {n} -> figs/{name}.png", file=sys.stderr)
