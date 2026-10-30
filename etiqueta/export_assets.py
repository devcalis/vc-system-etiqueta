"""
export_assets.py — Exporta logo + contornos de fonte para o gerador web.

Por quê: a página desenha a etiqueta em vetor (SVG na prévia, PDF no download)
com EXATAMENTE as mesmas formas do PDF aprovado. Em vez de carregar fontes
(CSP + regra de fontes da Envato), mandamos só os glifos usados, já em curva.

Saída: assets.json
  logo:  {aspect, polys:[[x,y,...]], gradient:[[t,"#hex"],...]}   (altura = 1)
  fonts: {key: {upm, cap, g: {char: [adv, cmds...]}}}
         cmds = ["M",x,y, "L",x,y, "C",x1,y1,x2,y2,x3,y3, "Z"]  (unidades da fonte, Y pra cima)
"""
import json
import sys

from fontTools.pens.basePen import BasePen
from fontTools.ttLib import TTFont

from vtext import FONTS

SETS = {
    "price": ("price", "0123456789,."),
    "rs": ("ui_bold", "R$"),
    "chip": ("ui_black", "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"),
    "digits": ("ui", "0123456789SOBRAimprefolhacm×/% "),
    "brand": ("brand", "OUTLET"),
    # nome do produto (sempre em maiúsculas na etiqueta): letras com acento do português e pontuação comum
    "name": ("ui", "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789ÁÀÂÃÄÉÈÊËÍÌÎÏÓÒÔÕÖÚÙÛÜÇÑ -/.,&+()'\"#%°ªº:!?*"),
}


class FlatPen(BasePen):
    def __init__(self, gs):
        super().__init__(gs)
        self.out = []

    def _moveTo(self, p):
        self.out += ["M", round(p[0]), round(p[1])]

    def _lineTo(self, p):
        self.out += ["L", round(p[0]), round(p[1])]

    def _curveToOne(self, a, b, c):
        self.out += ["C", round(a[0]), round(a[1]), round(b[0]), round(b[1]), round(c[0]), round(c[1])]

    def _closePath(self):
        self.out += ["Z"]


def export_font(path, chars):
    tt = TTFont(path)
    gs, cmap, hmtx = tt.getGlyphSet(), tt.getBestCmap(), tt["hmtx"]
    upm = tt["head"].unitsPerEm
    cap = getattr(tt["OS/2"], "sCapHeight", 0)
    if not cap:
        from fontTools.pens.boundsPen import BoundsPen
        bp = BoundsPen(gs)
        gs[cmap[ord("H")]].draw(bp)
        cap = bp.bounds[3]
    glyphs = {}
    for ch in dict.fromkeys(chars):
        gname = cmap.get(ord(ch))
        if gname is None:
            raise SystemExit(f"glifo ausente: {ch!r} em {path}")
        pen = FlatPen(gs)
        gs[gname].draw(pen)
        glyphs[ch] = [hmtx[gname][0]] + pen.out
    return {"upm": upm, "cap": cap, "g": glyphs}


def main(out):
    logo = json.load(open("logo_vc.json"))
    data = {
        "logo": {
            "aspect": round(logo["aspect"], 5),
            "polys": [[round(v, 5) for pt in poly for v in pt] for poly in logo["polys"]],
            "gradient": logo["gradient"],
        },
        "fonts": {k: export_font(FONTS[fk], chars) for k, (fk, chars) in SETS.items()},
    }
    with open(out, "w") as f:
        json.dump(data, f, separators=(",", ":"))
    print(out, len(json.dumps(data, separators=(",", ":"))), "bytes")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "assets.json")
