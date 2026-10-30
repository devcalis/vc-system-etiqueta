"""
preview.py — Prancha de aprovação (PNG): etiqueta ampliada nas duas versões + folhas inteiras.

uso: python3 preview.py <pasta_out> <preço> <tamanho> [ean]
Lê os PDFs gerados por sheet.py na mesma pasta e salva VC-Outlet_etiqueta-preview.png.
"""
import subprocess
import sys

from PIL import Image, ImageDraw, ImageFont
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

import sheet
from label import PRETA, TERMICA, H, W, brl_parts, draw_label

INTER = "/usr/share/fonts/opentype/inter/Inter-SemiBold.otf"
INTER_M = "/usr/share/fonts/opentype/inter/Inter-Medium.otf"
ADV = "/usr/share/texmf/fonts/opentype/public/tex-gyre/texgyreadventor-bold.otf"
BG, INK, MUTED, LINE = "#E7E5E1", "#151515", "#6B6D70", "#BEBBB5"


def _png(pdf, out_stem, dpi):
    subprocess.run(["pdftoppm", "-r", str(dpi), "-png", "-singlefile", pdf, out_stem], check=True)
    return Image.open(out_stem + ".png").convert("RGB")


def main(out, price, size, ean=None):
    d = sheet.product_data(price, size, ean)[0]
    labels = []
    for th in (PRETA, TERMICA):
        p = f"{out}/one_{th.name}.pdf"
        c = canvas.Canvas(p, pagesize=(W * mm, H * mm))
        draw_label(c, d, th, 0, 0, 0)
        c.showPage()
        c.save()
        labels.append(_png(p, f"{out}/one_{th.name}", 900))
    sheets = [_png(f"{out}/VC-Outlet_etiquetas-4x3_folha-10x15_{t}.pdf", f"{out}/sheet_{t}", 300)
              for t in ("PRETA", "TERMICA")]

    f = lambda p, s: ImageFont.truetype(p, s)
    colw, pad, gap = 1182, 70, 70
    labels = [l.resize((colw, int(l.height * colw / l.width)), Image.LANCZOS) for l in labels]
    Wpx = pad * 2 + colw * 2 + gap
    Hpx = pad + 150 + labels[0].height + 190 + sheets[0].height + pad
    im = Image.new("RGB", (Wpx, Hpx), BG)
    dr = ImageDraw.Draw(im)
    inteiro, cent = brl_parts(price)
    dr.text((pad, pad), "V C   O U T L E T", font=f(ADV, 44), fill=INK)
    dr.text((pad, pad + 64), f"Etiqueta 4 × 3 cm  ·  R$ {inteiro},{cent}  ·  tamanho {d.size}"
            "  ·  12 por folha 10 × 15 cm com linhas de corte", font=f(INTER_M, 30), fill=MUTED)
    y = pad + 150
    caps = [("PRETA", "impressora colorida, sem margem"), ("TÉRMICA", "impressora de etiqueta, 1 cor")]
    for i in range(2):
        x = pad + i * (colw + gap)
        im.paste(labels[i], (x, y))
        dr.rectangle([x - 1, y - 1, x + colw, y + labels[i].height], outline=LINE, width=1)
        t, s = caps[i]
        dr.text((x, y + labels[i].height + 28), t, font=f(INTER, 34), fill=INK)
        tw = dr.textlength(t, font=f(INTER, 34))
        dr.text((x + tw + 18, y + labels[i].height + 32), s, font=f(INTER_M, 30), fill=MUTED)
    y2 = y + labels[0].height + 190
    dr.text((pad, y2 - 58), "Folha inteira (tamanho real 10 × 15 cm)", font=f(INTER, 30), fill=INK)
    for i in range(2):
        x = pad + i * (colw + gap)
        im.paste(sheets[i], (x, y2))
        dr.rectangle([x - 1, y2 - 1, x + colw, y2 + sheets[i].height], outline=LINE, width=1)
    im.save(f"{out}/VC-Outlet_etiqueta-preview.png", optimize=True)


if __name__ == "__main__":
    main(sys.argv[1], float(sys.argv[2].replace(",", ".")), sys.argv[3],
         sys.argv[4] if len(sys.argv) > 4 else None)
