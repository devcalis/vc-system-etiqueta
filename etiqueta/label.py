"""
label.py — Desenho de UMA etiqueta VC Outlet 40 × 30 mm (coordenadas locais em mm,
origem no canto inferior esquerdo, Y pra cima).

Estrutura (de cima pra baixo):
  ┌──────────────────────────────────────┐
  │ [VC] │ OUTLET                  [ M ] │  ← lockup da marca + chip de tamanho
  │                                      │
  │ R$ 189,90                            │  ← preço protagonista (auto-ajuste)
  │ ┌──────────────────────────────────┐ │
  │ │ ||| |||| | ||||| || ||| |||| ||| │ │  ← painel do código (EAN-13)
  │ │ 2 001234 567890                  │ │
  │ └──────────────────────────────────┘ │
  └──────────────────────────────────────┘

Regras de produção embutidas:
  - Nada encosta na borda: tudo a ≥ 2,0 mm do corte (folga pra corte manual).
  - Tema PRETA: todas as bordas são pretas → erro de corte não mostra filete branco.
  - Tema TÉRMICA: 1 cor, sem degradê, traço mínimo 0,25 mm (2 pontos em 203 dpi).
  - Código de barras: módulo 0,25 mm = 2 pontos (203 dpi) / 3 pontos (300 dpi)
    → barras sempre com número inteiro de pontos na térmica.
"""
import json
import os
from dataclasses import dataclass

from reportlab.lib.colors import HexColor
from reportlab.lib.units import mm

import ean13
from vtext import font

W, H = 40.0, 30.0  # mm
HERE = os.path.dirname(os.path.abspath(__file__))
LOGO = json.load(open(os.path.join(HERE, "logo_vc.json")))


# ─────────────────────────────── Temas ───────────────────────────────
@dataclass(frozen=True)
class Theme:
    name: str
    bg: str
    metal: bool          # monograma com degradê prata (só impressão colorida)
    mono: str            # cor sólida do monograma quando metal=False
    ink: str             # preço
    ink_soft: str        # R$, centavos, OUTLET
    rule: str            # filete divisor
    rule_w: float        # mm
    chip_fill: str | None
    chip_stroke: str | None
    chip_text: str
    panel: str | None    # painel branco do código (None = sem painel)
    bars: str


PRETA = Theme(
    name="preta", bg="#0B0B0C", metal=True, mono="#D9DADB",
    ink="#F5F5F4", ink_soft="#A9ABAE", rule="#4A4B4D", rule_w=0.18,
    chip_fill=None, chip_stroke="#BFC1C3", chip_text="#F5F5F4",
    panel="#FFFFFF", bars="#000000",
)

TERMICA = Theme(
    name="termica", bg="#FFFFFF", metal=False, mono="#000000",
    ink="#000000", ink_soft="#000000", rule="#000000", rule_w=0.25,
    chip_fill="#000000", chip_stroke=None, chip_text="#FFFFFF",
    panel=None, bars="#000000",
)


@dataclass(frozen=True)
class LabelData:
    price: float
    size: str
    ean: str


# ─────────────────────────────── Grade ───────────────────────────────
M = 2.0                 # margem de segurança (mm)
X0 = M                  # eixo esquerdo = borda do painel (alinhamento único)
X1 = W - M              # eixo direito

PANEL = (M, M, W - M, 12.3)      # x0, y0, x1, y1
MOD = 0.25                       # módulo EAN (mm)
BAR_X = 8.75                     # início das barras (múltiplo de 0,25 → grade da térmica)
BAR_Y0, BAR_Y1 = 4.8, 11.4       # barras normais (6,6 mm)
GUARD_Y0 = BAR_Y0 - 5 * MOD      # barras-guia descem 5 módulos
DIGIT_BASE, DIGIT_CAP = 2.75, 1.75

ROW1_Y, ROW1_H = 22.7, 5.3       # lockup e chip (topo a 2,0 mm do corte)
PRICE_BASE = 14.45               # linha de base do preço
PRICE_CAP = 6.4                  # altura de maiúscula alvo do preço
PRICE_MAXW = X1 - X0


# ─────────────────────────────── Peças ───────────────────────────────
def _monogram(c, x, y, h, th: Theme):
    p = c.beginPath()
    for poly in LOGO["polys"]:
        p.moveTo((x + poly[0][0] * h) * mm, (y + poly[0][1] * h) * mm)
        for px, py in poly[1:]:
            p.lineTo((x + px * h) * mm, (y + py * h) * mm)
        p.close()
    if th.metal:
        c.saveState()
        c.clipPath(p, stroke=0, fill=0, fillMode=1)
        stops = LOGO["gradient"]
        c.linearGradient(
            x * mm, (y + h) * mm, x * mm, y * mm,
            [HexColor(col) for _, col in stops], [t for t, _ in stops],
            extend=True,
        )
        c.restoreState()
    else:
        c.setFillColor(HexColor(th.mono))
        c.drawPath(p, stroke=0, fill=1, fillMode=1)
    return LOGO["aspect"] * h


def _lockup(c, th: Theme):
    w = _monogram(c, X0, ROW1_Y, ROW1_H, th)
    # filete vertical entre monograma e palavra
    dx = X0 + w + 1.25
    c.setStrokeColor(HexColor(th.rule))
    c.setLineWidth(th.rule_w * mm)
    c.line(dx * mm, (ROW1_Y + 0.9) * mm, dx * mm, (ROW1_Y + ROW1_H - 0.9) * mm)
    f = font("brand")
    cap = 1.32
    size = cap / f.cap_height_ratio
    base = ROW1_Y + (ROW1_H - cap) / 2
    f.draw(c, "OUTLET", dx + 1.25, base, size, track=0.32, fill=HexColor(th.ink_soft))


def _size_chip(c, size_txt, th: Theme):
    s = ROW1_H
    x, y = X1 - s, ROW1_Y
    c.setLineWidth(0.22 * mm)
    if th.chip_fill:
        c.setFillColor(HexColor(th.chip_fill))
    if th.chip_stroke:
        c.setStrokeColor(HexColor(th.chip_stroke))
    c.roundRect(x * mm, y * mm, s * mm, s * mm, 0.9 * mm,
                stroke=1 if th.chip_stroke else 0, fill=1 if th.chip_fill else 0)
    f = font("ui_black")
    cap = 2.55 if len(size_txt) <= 2 else 2.0
    size = cap / f.cap_height_ratio
    maxw = s - 1.3
    w = f.width(size_txt, size, -0.02)
    if w > maxw:
        size *= maxw / w
        cap = size * f.cap_height_ratio
    f.draw(c, size_txt, x + s / 2, y + (s - cap) / 2, size, track=-0.02,
           fill=HexColor(th.chip_text), anchor="middle")


def brl_parts(value: float):
    inteiro, cent = f"{value:.2f}".split(".")
    inteiro = f"{int(inteiro):,}".replace(",", ".")
    return inteiro, cent


def _price(c, value: float, th: Theme):
    f = font("price")
    inteiro, cent = brl_parts(value)
    size = PRICE_CAP / f.cap_height_ratio
    cur_k, cent_k, gap_k = 0.36, 0.50, 0.10   # proporções relativas ao corpo do preço

    def layout(sz):
        cur_sz, cent_sz = sz * cur_k, sz * cent_k
        w_cur = font("ui_bold").width("R$", cur_sz, 0.0)
        w_int = f.width(inteiro, sz, -0.01)
        w_cent = f.width("," + cent, cent_sz, 0.0)
        total = w_cur + gap_k * sz + w_int + 0.04 * sz + w_cent
        return total, cur_sz, cent_sz, w_cur, w_int

    total, *_ = layout(size)
    if total > PRICE_MAXW:                      # auto-ajuste pra preço de 4 dígitos
        size *= PRICE_MAXW / total
    total, cur_sz, cent_sz, w_cur, w_int = layout(size)

    cap = size * f.cap_height_ratio
    top = PRICE_BASE + cap
    x = X0
    # R$ alinhado pelo topo da maiúscula
    ub = font("ui_bold")
    ub.draw(c, "R$", x, top - cur_sz * ub.cap_height_ratio, cur_sz, fill=HexColor(th.ink_soft))
    x += w_cur + gap_k * size
    f.draw(c, inteiro, x, PRICE_BASE, size, track=-0.01, fill=HexColor(th.ink))
    x += w_int + 0.04 * size
    # centavos sobrescritos (padrão de varejo), também alinhados pelo topo
    f.draw(c, "," + cent, x, top - cent_sz * f.cap_height_ratio, cent_sz,
           fill=HexColor(th.ink))


def _barcode(c, code: str, th: Theme):
    if th.panel:
        x0, y0, x1, y1 = PANEL
        c.setFillColor(HexColor(th.panel))
        c.roundRect(x0 * mm, y0 * mm, (x1 - x0) * mm, (y1 - y0) * mm, 1.0 * mm, stroke=0, fill=1)
    else:
        # térmica: filete separando a zona do código
        c.setStrokeColor(HexColor(th.rule))
        c.setLineWidth(th.rule_w * mm)
        c.line(X0 * mm, PANEL[3] * mm, X1 * mm, PANEL[3] * mm)

    bits = ean13.encode(code)
    guards = ean13.guard_mask()
    c.setFillColor(HexColor(th.bars))
    i = 0
    while i < 95:                               # agrupa módulos contíguos em 1 barra
        if bits[i] == "1":
            j = i
            while j < 95 and bits[j] == "1":
                j += 1
            y0 = GUARD_Y0 if guards[i] else BAR_Y0
            c.rect((BAR_X + i * MOD) * mm, y0 * mm, (j - i) * MOD * mm,
                   (BAR_Y1 - y0) * mm, stroke=0, fill=1)
            i = j
        else:
            i += 1

    # dígitos legíveis no padrão EAN: 1º fora, 6 sob cada metade
    f = font("ui")
    size = DIGIT_CAP / f.cap_height_ratio
    ink = HexColor(th.bars)
    f.draw(c, code[0], BAR_X - 1.0, DIGIT_BASE, size, fill=ink, anchor="end")
    for k in range(6):
        cx = BAR_X + (3 + 7 * k + 3.5) * MOD
        f.draw(c, code[1 + k], cx, DIGIT_BASE, size, fill=ink, anchor="middle")
        cx = BAR_X + (50 + 7 * k + 3.5) * MOD
        f.draw(c, code[7 + k], cx, DIGIT_BASE, size, fill=ink, anchor="middle")


# ─────────────────────────────── API ───────────────────────────────
def draw_label(c, data: LabelData, th: Theme, x: float, y: float, rot: int = 0):
    """Desenha a etiqueta com o canto inferior esquerdo da sua CAIXA na folha em (x, y) mm.
    rot ∈ {0, 90, 180, 270}; com 90/270 a caixa ocupa 30 × 40 mm."""
    c.saveState()
    if rot == 0:
        c.translate(x * mm, y * mm)
    elif rot == 180:
        c.translate((x + W) * mm, (y + H) * mm)
        c.rotate(180)
    elif rot == 90:
        c.translate((x + H) * mm, y * mm)
        c.rotate(90)
    elif rot == 270:
        c.translate(x * mm, (y + W) * mm)
        c.rotate(-90)
    else:
        raise ValueError("rot precisa ser 0, 90, 180 ou 270")

    c.setFillColor(HexColor(th.bg))
    c.rect(0, 0, W * mm, H * mm, stroke=0, fill=1)
    _lockup(c, th)
    _size_chip(c, data.size, th)
    _price(c, data.price, th)
    _barcode(c, data.ean, th)
    c.restoreState()
