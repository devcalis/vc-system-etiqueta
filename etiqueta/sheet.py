"""
sheet.py — Folha 100 × 150 mm com 12 etiquetas 40 × 30 mm (máximo possível).

Por que 12 e não 10:
  Grade simples (2 × 5) = 10 etiquetas e sobra uma faixa de 2 × 15 cm.
  Área: 150 cm² ÷ 12 cm² = 12,5 → o teto é 12. O encaixe abaixo chega nele
  usando 10 = 4 + 3 + 3 (uma coluna deitada + duas colunas em pé):

     x: 0        40      70      100
  150 ┌─────────┬───────┬───────┐
      │  A1     │  B1   │  C1   │
  120 ├─────────┤ (em   │ (em   │
      │  A2     │  pé)  │  pé)  │
   90 ├─────────┼───────┼───────┤ 110
      │  A3     │  B2   │  C2   │
   60 ├─────────┤       │       │
      │  A4     ├───────┼───────┤ 70
   30 ├─────────┤  B3   │  C3   │
      │  A5     ├───────┴─┬─────┤ 30
    0 │         │   D1    │sobra│
      └─────────┴─────────┴─────┘
  Sobra total: 2 × 3 cm (6 cm²). Todos os cortes são retos de ponta a ponta
  (dá pra usar guilhotina/refiladora).

Saídas:
  VC-Outlet_etiquetas-4x3_folha-10x15_PRETA.pdf    (jato de tinta/laser colorida, sem margem)
  VC-Outlet_etiquetas-4x3_folha-10x15_TERMICA.pdf  (impressora térmica, 1 cor)
"""
import random
import sys

from reportlab.lib.colors import HexColor
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

import ean13
from label import PRETA, TERMICA, LabelData, Theme, draw_label
from vtext import font

PAGE_W, PAGE_H = 100.0, 150.0

# (id, x, y, rot) — canto inferior esquerdo da CAIXA da etiqueta, em mm
SLOTS = [
    ("A1", 0, 120, 0), ("A2", 0, 90, 0), ("A3", 0, 60, 0), ("A4", 0, 30, 0), ("A5", 0, 0, 0),
    ("B1", 40, 110, 90), ("B2", 40, 70, 90), ("B3", 40, 30, 90),
    ("C1", 70, 110, 90), ("C2", 70, 70, 90), ("C3", 70, 30, 90),
    ("D1", 40, 0, 0),
]
WASTE = (80, 0, 20, 30)  # x, y, w, h

# Marcas de corte na borda da folha (posição em mm)
TICKS = {
    "top": [40, 70], "bottom": [40, 80],
    "left": [30, 60, 90, 120], "right": [30, 70, 110],
}
TICK_LEN, TICK_W = 1.5, 0.2

# Linhas de corte internas (x0, y0, x1, y1) — mesmas posições do guia de corte.
# Só as internas: a borda do papel já é o corte de fora.
CUT_LINES = [
    (40, 0, 40, 150),                                   # 1 · vertical principal
    (0, 120, 40, 120), (0, 90, 40, 90), (0, 60, 40, 60), (0, 30, 40, 30),  # 2
    (40, 30, 100, 30),                                  # 3
    (70, 30, 70, 150),                                  # 4
    (40, 110, 100, 110), (40, 70, 100, 70),             # 5
    (80, 0, 80, 30),                                    # 6 · separa a sobra
]
# Preta: cinza médio (visível no preto, quase some se o corte desviar).
# Térmica: preto 0,25 mm = 2 pontos em 203 dpi (traço mais fino some na térmica).
CUT_STYLE = {"preta": ("#8E9093", 0.2), "termica": ("#000000", 0.25)}


def demo_data(seed: int = 7) -> list:
    """Dados ALEATÓRIOS só pra teste (preço, tamanho e EAN-13 interno prefixo 2)."""
    rng = random.Random(seed)
    precos = [39.90, 49.90, 59.90, 79.90, 89.90, 99.90, 119.90, 129.90,
              149.90, 189.90, 249.90, 299.90]
    tamanhos = ["PP", "P", "M", "G", "GG", "XG", "36", "38", "40", "42", "44", "U"]
    rng.shuffle(precos)
    rng.shuffle(tamanhos)
    precos[3] = 1049.90          # força um preço de 4 dígitos pra testar o auto-ajuste
    return [LabelData(precos[i], tamanhos[i], ean13.random_store_code(rng)) for i in range(12)]


def _ticks(c, color: str):
    c.setFillColor(HexColor(color))
    for x in TICKS["top"]:
        c.rect((x - TICK_W / 2) * mm, (PAGE_H - TICK_LEN) * mm, TICK_W * mm, TICK_LEN * mm, 0, 1)
    for x in TICKS["bottom"]:
        c.rect((x - TICK_W / 2) * mm, 0, TICK_W * mm, TICK_LEN * mm, 0, 1)
    for y in TICKS["left"]:
        c.rect(0, (y - TICK_W / 2) * mm, TICK_LEN * mm, TICK_W * mm, 0, 1)
    for y in TICKS["right"]:
        c.rect((PAGE_W - TICK_LEN) * mm, (y - TICK_W / 2) * mm, TICK_LEN * mm, TICK_W * mm, 0, 1)


def _waste_note(c, th: Theme):
    """Na sobra (2 × 3 cm) vai a identificação da folha — não ocupa etiqueta."""
    x, y, w, h = WASTE
    c.setFillColor(HexColor(th.bg))
    c.rect(x * mm, y * mm, w * mm, h * mm, stroke=0, fill=1)
    ink = HexColor("#6B6D70" if th.name == "preta" else "#000000")
    f = font("ui")
    cx = x + w / 2
    lines = ["SOBRA", "4×3 cm", "12/folha", "imprimir", "em 100%"]
    yy = y + h - 9
    for i, t in enumerate(lines):
        f.draw(c, t, cx, yy - i * 2.6, 1.55 if i else 1.7, track=0.06 if i == 0 else 0,
               fill=ink, anchor="middle")


def _cut_lines(c, th: Theme):
    color, width = CUT_STYLE[th.name]
    c.setStrokeColor(HexColor(color))
    c.setLineWidth(width * mm)
    c.setLineCap(0)  # ponta reta: a linha termina exatamente na borda
    for x0, y0, x1, y1 in CUT_LINES:
        c.line(x0 * mm, y0 * mm, x1 * mm, y1 * mm)


def build(path: str, th: Theme, data: list, cut_lines: bool = True):
    c = canvas.Canvas(path, pagesize=(PAGE_W * mm, PAGE_H * mm))
    c.setTitle(f"VC Outlet — etiquetas 4x3 cm — folha 10x15 ({th.name})")
    c.setAuthor("KeyCodes")
    c.setFillColor(HexColor(th.bg))
    c.rect(0, 0, PAGE_W * mm, PAGE_H * mm, stroke=0, fill=1)
    for (sid, x, y, rot), d in zip(SLOTS, data):
        draw_label(c, d, th, x, y, rot)
    _waste_note(c, th)
    if cut_lines:
        _cut_lines(c, th)          # contorno de corte visível em cada etiqueta
    else:
        _ticks(c, "#5C5E61" if th.name == "preta" else "#6E6E6E")
    c.showPage()
    c.save()


def product_data(price: float, size: str, ean: str | None = None, seed: int = 11) -> list:
    """Folha de UM produto: as 12 etiquetas iguais, mesmo EAN (mesmo item no caixa)."""
    code = ean or ean13.random_store_code(random.Random(seed))
    ean13.encode(code)  # valida o dígito verificador
    return [LabelData(price, size.upper(), code) for _ in range(len(SLOTS))]


if __name__ == "__main__":
    # uso: python3 sheet.py <pasta> [preço tamanho [ean]]   ex.: sheet.py out 119.99 G
    out = sys.argv[1] if len(sys.argv) > 1 else "."
    if len(sys.argv) >= 4:
        data = product_data(float(sys.argv[2].replace(",", ".")), sys.argv[3],
                            sys.argv[4] if len(sys.argv) > 4 else None)
    else:
        data = demo_data()
    build(f"{out}/VC-Outlet_etiquetas-4x3_folha-10x15_PRETA.pdf", PRETA, data)
    build(f"{out}/VC-Outlet_etiquetas-4x3_folha-10x15_TERMICA.pdf", TERMICA, data)
    for (sid, *_), d in zip(SLOTS, data):
        print(sid, d.ean, f"{d.price:.2f}", d.size)
