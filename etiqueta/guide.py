"""
guide.py — Guia de corte (PDF A4 paisagem → PNG pra ver no celular).

Mostra a folha 10 × 15 em escala 1:1 com as 12 etiquetas, a sobra e os cortes
numerados na ordem certa. Todos os cortes vão de ponta a ponta da peça.
"""
import sys

from reportlab.lib.colors import HexColor
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

import sheet
from vtext import font

A4L = (297.0, 210.0)
OX, OY = 22.0, 20.0                     # origem da folha no guia
INK = HexColor("#151515")
MUTED = HexColor("#6B6D70")
ACCENT = HexColor("#D9472B")            # linha de corte
LIGHT = HexColor("#F2F1EE")

# (nº, x0, y0, x1, y1) em mm da folha — ordem de corte
CUTS = [
    (1, 40, 0, 40, 150),
    (2, 0, 120, 40, 120), (2, 0, 90, 40, 90), (2, 0, 60, 40, 60), (2, 0, 30, 40, 30),
    (3, 40, 30, 100, 30),
    (4, 70, 30, 70, 150),
    (5, 40, 110, 100, 110), (5, 40, 70, 100, 70),
    (6, 80, 0, 80, 30),
]
STEPS = [
    ("1", "Corte vertical a 4 cm da esquerda, de cima a baixo."),
    ("2", "Na tira da esquerda (4 cm): corte a cada 3 cm → 5 etiquetas."),
    ("3", "No bloco da direita (6 cm): corte a 3 cm do pé."),
    ("4", "No bloco de cima (6 × 12 cm): corte vertical no meio (3 cm)."),
    ("5", "Em cada tira de 3 × 12 cm: corte a cada 4 cm → 6 etiquetas."),
    ("6", "Na faixa do pé (6 × 3 cm): corte a 4 cm → 1 etiqueta + sobra."),
]


def _txt(c, key, s, x, y, cap, fill=INK, anchor="start", track=0.0):
    f = font(key)
    return f.draw(c, s, x, y, cap / f.cap_height_ratio, track=track, fill=fill, anchor=anchor)


def build(path):
    c = canvas.Canvas(path, pagesize=(A4L[0] * mm, A4L[1] * mm))
    c.setFillColor(HexColor("#FFFFFF"))
    c.rect(0, 0, A4L[0] * mm, A4L[1] * mm, 0, 1)

    # título
    _txt(c, "brand", "VC OUTLET", OX, 196, 3.4, track=0.28)
    _txt(c, "ui", "Guia de corte · folha 10 × 15 cm → 12 etiquetas de 4 × 3 cm · escala 1:1", OX, 189.5, 2.1, MUTED)

    # folha
    c.setFillColor(LIGHT)
    c.setStrokeColor(INK)
    c.setLineWidth(0.35 * mm)
    c.rect(OX * mm, OY * mm, 100 * mm, 150 * mm, stroke=1, fill=1)
    for sid, x, y, rot in sheet.SLOTS:
        w, h = (40, 30) if rot in (0, 180) else (30, 40)
        c.setFillColor(HexColor("#FFFFFF"))
        c.setStrokeColor(HexColor("#C9C7C2"))
        c.setLineWidth(0.25 * mm)
        c.rect((OX + x + 0.8) * mm, (OY + y + 0.8) * mm, (w - 1.6) * mm, (h - 1.6) * mm, 1, 1)
        _txt(c, "ui_bold", sid, OX + x + w / 2, OY + y + h / 2 + 0.3, 3.2, INK, "middle")
        _txt(c, "ui", "deitada" if rot in (0, 180) else "em pé", OX + x + w / 2,
             OY + y + h / 2 - 4.2, 1.7, MUTED, "middle")
    # sobra hachurada
    x, y, w, h = sheet.WASTE
    c.saveState()
    p = c.beginPath()
    p.rect((OX + x) * mm, (OY + y) * mm, w * mm, h * mm)
    c.clipPath(p, stroke=0, fill=0)
    c.setStrokeColor(HexColor("#BDBAB4"))
    c.setLineWidth(0.25 * mm)
    for k in range(-40, 40, 3):
        c.line((OX + x + k) * mm, (OY + y) * mm, (OX + x + k + 30) * mm, (OY + y + 30) * mm)
    c.restoreState()
    _txt(c, "ui_bold", "sobra", OX + x + w / 2, OY + y + h / 2 - 1, 2.1, MUTED, "middle")

    # cortes numerados
    c.setStrokeColor(ACCENT)
    c.setLineWidth(0.55 * mm)
    c.setDash(3, 1.6)
    for n, x0, y0, x1, y1 in CUTS:
        c.line((OX + x0) * mm, (OY + y0) * mm, (OX + x1) * mm, (OY + y1) * mm)
    c.setDash()
    seen = set()
    for n, x0, y0, x1, y1 in CUTS:
        if n in seen:
            continue
        seen.add(n)
        # bolinha com o número na ponta do corte, fora da folha
        if x0 == x1:   # vertical
            bx, by = OX + x0, OY + (y1 + 4.5 if y1 == 150 else y0 - 4.5)
        else:          # horizontal
            bx, by = (OX + x0 - 4.5, OY + y0) if x0 == 0 else (OX + x1 + 4.5, OY + y0)
        c.setFillColor(ACCENT)
        c.circle(bx * mm, by * mm, 2.6 * mm, stroke=0, fill=1)
        _txt(c, "ui_bold", str(n), bx, by - 1.0, 2.0, HexColor("#FFFFFF"), "middle")

    # medidas
    _txt(c, "ui", "10 cm", OX + 50, OY - 7.5, 1.9, MUTED, "middle")
    c.saveState()
    c.translate((OX - 9.5) * mm, (OY + 75) * mm)
    c.rotate(90)
    _txt(c, "ui", "15 cm", 0, 0, 1.9, MUTED, "middle")
    c.restoreState()

    # passo a passo
    tx = OX + 100 + 22
    _txt(c, "ui_bold", "Ordem de corte", tx, 176, 3.0)
    yy = 165
    for n, s in STEPS:
        c.setFillColor(ACCENT)
        c.circle((tx + 2.6) * mm, (yy + 1.1) * mm, 2.6 * mm, stroke=0, fill=1)
        _txt(c, "ui_bold", n, tx + 2.6, yy + 0.1, 2.0, HexColor("#FFFFFF"), "middle")
        _txt(c, "ui", s, tx + 8, yy, 2.05, INK)
        yy -= 9.5

    yy -= 4
    _txt(c, "ui_bold", "Antes de imprimir", tx, yy, 2.6)
    notes = [
        "Imprima em TAMANHO REAL (100%). Nunca \"ajustar à página\".",
        "Versão PRETA: impressão SEM MARGEM (borderless), papel fotográfico/adesivo.",
        "Versão TÉRMICA: etiqueta 100 × 150 mm, mesma que a de envio.",
        "Os risquinhos na borda da folha marcam onde cortar.",
        "Use régua de aço + estilete ou refiladora. Etiqueta tem 2 mm de folga.",
    ]
    yy -= 8
    for s in notes:
        c.setFillColor(INK)
        c.circle((tx + 1.0) * mm, (yy + 0.9) * mm, 0.6 * mm, stroke=0, fill=1)
        _txt(c, "ui", s, tx + 4, yy, 1.85, INK)
        yy -= 6.4

    c.showPage()
    c.save()


if __name__ == "__main__":
    build(sys.argv[1] if len(sys.argv) > 1 else "out/guia-de-corte.pdf")
