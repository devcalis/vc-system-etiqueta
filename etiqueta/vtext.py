"""
vtext.py — Texto convertido em curva direto no PDF (reportlab + fontTools).

Por quê: o reportlab só embute TrueType, e as fontes boas aqui são OpenType/CFF.
Desenhando o contorno de cada glifo, o PDF sai com TEXTO EM CURVA (o que gráfica
pede) e funciona com qualquer .otf/.ttf — inclusive a fonte da Envato depois,
é só trocar o caminho em FONTS.

API:
  font(key)                         → objeto VFont (cacheado)
  VFont.width(text, size_mm, track) → largura em mm
  VFont.draw(canvas, text, x, y, size_mm, track=0, fill=None, anchor="start")
       desenha com a linha de base em y (mm). track = espaçamento em em.
  VFont.cap_height_ratio            → altura de maiúscula / em
"""
from functools import lru_cache

from fontTools.pens.basePen import BasePen
from fontTools.ttLib import TTFont
from reportlab.lib.units import mm

FONTS = {
    # provisórias (a definitiva vem da Envato) — todas convertidas em curva
    "price": "/usr/share/texmf/fonts/opentype/public/tex-gyre/texgyreheroscn-bold.otf",
    "brand": "/usr/share/texmf/fonts/opentype/public/tex-gyre/texgyreadventor-bold.otf",
    "ui": "/usr/share/fonts/opentype/inter/Inter-SemiBold.otf",
    "ui_bold": "/usr/share/fonts/opentype/inter/InterDisplay-Bold.otf",
    "ui_black": "/usr/share/fonts/opentype/inter/InterDisplay-Black.otf",
}


class _RLPen(BasePen):
    """Pen do fontTools que escreve num path do reportlab (com escala e offset)."""

    def __init__(self, glyphset, path, scale, ox, oy):
        super().__init__(glyphset)
        self.p, self.s, self.ox, self.oy = path, scale, ox, oy

    def _t(self, pt):
        return self.ox + pt[0] * self.s, self.oy + pt[1] * self.s

    def _moveTo(self, pt):
        self.p.moveTo(*self._t(pt))

    def _lineTo(self, pt):
        self.p.lineTo(*self._t(pt))

    def _curveToOne(self, p1, p2, p3):
        self.p.curveTo(*self._t(p1), *self._t(p2), *self._t(p3))

    def _closePath(self):
        self.p.close()


class VFont:
    def __init__(self, path):
        self.tt = TTFont(path)
        self.gs = self.tt.getGlyphSet()
        self.cmap = self.tt.getBestCmap()
        self.upm = self.tt["head"].unitsPerEm
        self.hmtx = self.tt["hmtx"]
        os2 = self.tt["OS/2"]
        cap = getattr(os2, "sCapHeight", 0) or self._measure_cap()
        self.cap_height_ratio = cap / self.upm

    def _measure_cap(self):
        from fontTools.pens.boundsPen import BoundsPen
        bp = BoundsPen(self.gs)
        self.gs[self.cmap[ord("H")]].draw(bp)
        return bp.bounds[3]

    def _glyph(self, ch):
        return self.cmap.get(ord(ch)) or self.cmap.get(ord("?"))

    def width(self, text, size_mm, track=0.0):
        if not text:
            return 0.0
        adv = sum(self.hmtx[self._glyph(c)][0] for c in text) / self.upm
        return (adv + track * (len(text) - 1)) * size_mm

    def draw(self, c, text, x, y, size_mm, track=0.0, fill=None, anchor="start"):
        """x, y em mm (linha de base). Retorna a largura desenhada em mm."""
        w = self.width(text, size_mm, track)
        if anchor == "middle":
            x -= w / 2
        elif anchor == "end":
            x -= w
        path = c.beginPath()
        s = size_mm * mm / self.upm
        cx = x * mm
        for ch in text:
            g = self._glyph(ch)
            self.gs[g].draw(_RLPen(self.gs, path, s, cx, y * mm))
            cx += self.hmtx[g][0] * s + track * size_mm * mm
        if fill is not None:
            c.setFillColor(fill)
        c.drawPath(path, stroke=0, fill=1, fillMode=1)  # 1 = non-zero (padrão de fonte)
        return w


@lru_cache(maxsize=None)
def font(key: str) -> VFont:
    return VFont(FONTS[key])
