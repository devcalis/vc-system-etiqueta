"""
logo_trace.py — Vetoriza o monograma "VC" a partir do JPG do cliente.

Pipeline:
  1. Recorta só o monograma (o subtítulo apagado do arquivo fica de fora).
  2. Binariza (logo prata sobre fundo preto) e amplia 6x com suavização,
     pra o contorno sair em subpixel e sem serrilhado do JPG.
  3. Marching squares (skimage.find_contours) no nível 0.5 → contornos.
  4. Simplifica (Douglas-Peucker) com tolerância bem abaixo do que a
     impressão consegue mostrar (~0,01 mm no tamanho da etiqueta).
  5. Normaliza: origem no canto inferior esquerdo, altura = 1.0, eixo Y pra cima
     (padrão PDF). Salva em JSON junto com as paradas do gradiente prata,
     amostradas do próprio logo.

Saída: logo_vc.json  →  {"aspect": w/h, "polys": [[[x,y],...],...], "gradient": [...]}
"""
import json
import sys

import numpy as np
from PIL import Image, ImageFilter
from skimage import measure

SRC = sys.argv[1] if len(sys.argv) > 1 else "src/logo-vc.jpg"
OUT = sys.argv[2] if len(sys.argv) > 2 else "logo_vc.json"

CROP = (232, 568, 816, 956)   # bbox medido do monograma (244..803, 580..944) + folga
SCALE = 6                     # ampliação antes do contorno
THRESH = 60                   # prata (>=95) vs fundo preto (<=20)
SIMPLIFY_PX = 0.6             # tolerância em px da imagem original (~0,01 mm impresso)

# Gradiente amostrado na coluna do "C" (topo → base), 0..1 da altura do monograma.
GRADIENT = [
    (0.00, "#9b9b9b"),
    (0.12, "#ababab"),
    (0.25, "#dadada"),
    (0.34, "#f6f6f6"),
    (0.43, "#e6e7e7"),
    (0.55, "#d3d5d7"),
    (0.75, "#b4b8bb"),
    (1.00, "#94989b"),
]


def trace(path: str) -> dict:
    img = Image.open(path).convert("L").crop(CROP)
    binary = img.point(lambda v: 255 if v > THRESH else 0)
    big = binary.resize((img.width * SCALE, img.height * SCALE), Image.LANCZOS)
    big = big.filter(ImageFilter.GaussianBlur(SCALE * 0.8))
    arr = np.asarray(big).astype(float) / 255.0
    # moldura de zeros garante contornos fechados
    arr = np.pad(arr, 2, constant_values=0.0)

    contours = measure.find_contours(arr, 0.5)
    polys = []
    for c in contours:
        if len(c) < 20:
            continue
        simp = measure.approximate_polygon(c, tolerance=SIMPLIFY_PX * SCALE)
        # (row, col) → (x, y) em px originais, sem o pad
        pts = [((col - 2) / SCALE, (row - 2) / SCALE) for row, col in simp]
        polys.append(pts)

    allpts = np.array([p for poly in polys for p in poly])
    x0, y0 = allpts.min(axis=0)
    x1, y1 = allpts.max(axis=0)
    h = y1 - y0
    norm = [[[(x - x0) / h, (y1 - y) / h] for x, y in poly] for poly in polys]
    return {
        "aspect": (x1 - x0) / h,
        "polys": norm,
        "gradient": GRADIENT,
        "source_px": [float(x1 - x0), float(h)],
    }


if __name__ == "__main__":
    data = trace(SRC)
    with open(OUT, "w") as f:
        json.dump(data, f)
    n = sum(len(p) for p in data["polys"])
    print(f"polys={len(data['polys'])} pts={n} aspect={data['aspect']:.4f} src={data['source_px']}")
