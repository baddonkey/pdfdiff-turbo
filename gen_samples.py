import os
from pathlib import Path
import fitz

def make_pdf(path: Path, lines):
    doc = fitz.open()
    for line in lines:
        page = doc.new_page()
        page.insert_text((72, 72), line, fontsize=14)
    path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(path)
    doc.close()

base = Path("/data/samples")
sets = ["set1", "set2", "set3", "set4"]
for s in sets:
    for folder in ("A", "B"):
        (base / s / folder).mkdir(parents=True, exist_ok=True)

make_pdf(base / "set1" / "A" / "alpha.pdf", ["Alpha Page 1", "Alpha Page 2", "Alpha Page 3"])
make_pdf(base / "set1" / "A" / "beta.pdf", ["Beta Page 1", "Beta Page 2"])
make_pdf(base / "set1" / "B" / "alpha.pdf", ["Alpha Page 1", "Alpha Page 2 (changed)", "Alpha Page 3"])
make_pdf(base / "set1" / "B" / "beta.pdf", ["Beta Page 1", "Beta Page 2"])

make_pdf(base / "set2" / "A" / "gamma.pdf", ["Gamma Page 1", "Gamma Page 2"])
make_pdf(base / "set2" / "A" / "delta.pdf", ["Delta Page 1", "Delta Page 2", "Delta Page 3"])
make_pdf(base / "set2" / "B" / "gamma.pdf", ["Gamma Page 1", "Gamma Page 2 (changed)"])
make_pdf(base / "set2" / "B" / "delta.pdf", ["Delta Page 1", "Delta Page 2", "Delta Page 3"])

make_pdf(base / "set3" / "A" / "epsilon.pdf", ["Epsilon Page 1", "Epsilon Page 2"])
make_pdf(base / "set3" / "A" / "zeta.pdf", ["Zeta Page 1", "Zeta Page 2", "Zeta Page 3"])
make_pdf(base / "set3" / "B" / "epsilon.pdf", ["Epsilon Page 1", "Epsilon Page 2"])
make_pdf(base / "set3" / "B" / "zeta.pdf", ["Zeta Page 1 (changed)", "Zeta Page 2", "Zeta Page 3"])

make_pdf(base / "set4" / "A" / "eta.pdf", ["Eta Page 1", "Eta Page 2"])
make_pdf(base / "set4" / "A" / "theta.pdf", ["Theta Page 1", "Theta Page 2", "Theta Page 3"])
make_pdf(base / "set4" / "B" / "eta.pdf", ["Eta Page 1", "Eta Page 2"])
make_pdf(base / "set4" / "B" / "theta.pdf", ["Theta Page 1", "Theta Page 2 (changed)", "Theta Page 3"])

print("done")
