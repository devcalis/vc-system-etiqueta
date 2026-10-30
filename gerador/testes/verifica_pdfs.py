"""
verifica_pdfs.py — confere os PDFs que os testes do navegador geraram.

Para cada PDF:
  - abre com pypdf (estrutura válida) e confere o número de páginas
  - cada página tem exatamente 100 × 150 mm
  - lê o EAN-13 de cada uma das 12 posições e compara com o esperado,
    em 300 dpi (jato de tinta/laser) e 203 dpi sem suavização (térmica).
    Posição vazia tem que sair sem código.

uso: python3 gerador/testes/verifica_pdfs.py gerador/testes/saida
"""
import os
import subprocess
import sys
import tempfile

import cv2
from pypdf import PdfReader

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "etiqueta"))
import verify  # noqa: E402  (decodificador + recorte por posição)

A, B = "2787789328799", "2000000014029"   # códigos usados nos testes
CODE = {1: A, 2: B, None: ""}

# arquivo → páginas → produto (1, 2 ou None=vazia) em cada posição A1…A5, B1…B3, C1…C3, D1
CASES = {
    "t6_troca3.pdf": [[2, 2, 1, 1, 1, 2, 1, 1, 1, 1, 1, 1]],
    "t6_vazia.pdf": [[2, 2, 1, 1, 1, 2, 1, 1, 1, 1, 1, None]],
    "t6_duas.pdf": [[2, 2, 1, 1, 1, 2, 1, 1, 1, 1, 1, 2], [2, 2] + [1] * 10],
    "t7_nome.pdf": [[2, 2, 1, 1, 1, 2, 1, 1, 1, 1, 1, 1]],
    "t8_preta.pdf": [[2] + [1] * 11],
    "t8_branca.pdf": [[2] + [1] * 11],   # etiqueta branca
}


def page_img(pdf, n, dpi, aa=True):
    with tempfile.TemporaryDirectory() as d:
        args = ["pdftoppm", "-f", str(n), "-l", str(n), "-r", str(dpi), "-gray", "-png", "-singlefile"]
        if not aa:
            args += ["-aa", "no", "-aaVector", "no"]
        subprocess.run(args + [pdf, f"{d}/p"], check=True)
        return cv2.imread(f"{d}/p.png", cv2.IMREAD_GRAYSCALE)


def check(pdf, pages):
    r = PdfReader(pdf)
    ok = len(r.pages) == len(pages)
    print(f"{os.path.basename(pdf)}: {len(r.pages)} página(s)" + ("" if ok else f"  ERRO: esperado {len(pages)}"))
    det = cv2.barcode.BarcodeDetector()
    for n, exp in enumerate(pages, 1):
        box = r.pages[n - 1].mediabox
        w, h = float(box.width) * 25.4 / 72, float(box.height) * 25.4 / 72
        size_ok = abs(w - 100) < 0.01 and abs(h - 150) < 0.01
        line = f"  pág {n}: {w:.2f} × {h:.2f} mm {'OK' if size_ok else 'ERRO'}"
        ok &= size_ok
        for name, dpi, aa in (("300 dpi", 300, True), ("203 dpi térmica", 203.2, False)):
            img = page_img(pdf, n, dpi, aa)
            if not aa:
                _, img = cv2.threshold(img, 128, 255, cv2.THRESH_BINARY)
            img = cv2.GaussianBlur(img, (0, 0), 0.8)   # lente do leitor
            got = [verify.decode(det, cr) for _, cr in verify.crops(img, dpi)]
            hits = sum(g == CODE[e] for g, e in zip(got, exp))
            ok &= hits == len(exp)
            line += f" | {name} {hits}/{len(exp)}"
        print(line)
    return ok


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "saida")
    ok = True
    for f, pages in CASES.items():
        p = os.path.join(out, f)
        if not os.path.exists(p):
            print(f"{f}: não encontrado (rode os testes do navegador antes)")
            ok = False
            continue
        ok &= check(p, pages)
    print("\nRESULTADO:", "TUDO OK" if ok else "TEM FALHA")
    sys.exit(0 if ok else 1)
