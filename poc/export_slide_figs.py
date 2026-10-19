"""Export the example slides of the full deck PROPOSAL_slides_full.pptx as figures for PROPOSAL.md (figs/ex_finding1-7.png, figs/ex_method.png): slide -> PDF (LibreOffice)
-> PNG at 150 dpi (pdftoppm), cropped to the content (slide title and footer removed).
usage: python poc/export_slide_figs.py   (needs soffice and pdftoppm; rebuild the deck first with node poc/make_slides.js)"""
import os, shutil, subprocess, sys, tempfile
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SLIDES = {5: "ex_finding1", 6: "ex_finding2", 7: "ex_finding3", 8: "ex_finding4", 9: "ex_finding5", 10: "ex_finding6", 11: "ex_finding7",
          13: "ex_method"}

with tempfile.TemporaryDirectory() as d:
    shutil.copy(os.path.join(ROOT, "PROPOSAL_slides_full.pptx"), d)
    subprocess.run(["soffice", "--headless", "--convert-to", "pdf", "--outdir", d, os.path.join(d, "PROPOSAL_slides_full.pptx")], check=True,
                   stdout=subprocess.DEVNULL)
    for n, name in SLIDES.items():
        subprocess.run(["pdftoppm", "-png", "-r", "150", "-f", str(n), "-l", str(n), "-singlefile", os.path.join(d, "PROPOSAL_slides_full.pdf"),
                        os.path.join(d, name)], check=True)
        im = Image.open(os.path.join(d, name + ".png")).convert("RGB")
        w, h = im.size
        im.crop((0, int(h * 1.22 / 7.5), w, int(h * 6.85 / 7.5))).save(os.path.join(ROOT, "figs", name + ".png"), optimize=True)
        print("wrote figs/" + name + ".png", file=sys.stderr)
