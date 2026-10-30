"""
verify.py — Conferência automática antes de entregar.

1. Tamanho do PDF: exatamente 100 × 150 mm.
2. Leitura dos 12 EAN-13: rasteriza a folha, recorta cada etiqueta pelo SLOT,
   desvira as que estão em pé e decodifica com o leitor de barras do OpenCV.
   Roda em 3 cenários:
     - 300 dpi com antisserrilhado (jato de tinta/laser)
     - 203 dpi SEM antisserrilhado, binarizado (simula térmica 8 pontos/mm)
     - 203 dpi térmica + GANHO DE PONTO: cada barra engorda ~0,03 mm por lado
       (≈25% de um módulo, típico de térmica direta) e o leitor vê com borrão
       maior. É o pior caso realista de loja.
   Todo cenário recebe um borrão óptico leve (σ≈0,8 px), que é o que a lente de
   um leitor real enxerga. O detector do OpenCV não lê imagem 100% nítida —
   testado: ele também falha no código de exemplo do cliente sem esse borrão.
"""
import subprocess
import sys
import tempfile

import cv2
import numpy as np
from pypdf import PdfReader

import sheet

MM_PT = 72 / 25.4


def page_size_mm(pdf):
    box = PdfReader(pdf).pages[0].mediabox
    return float(box.width) / MM_PT, float(box.height) / MM_PT


def raster(pdf, dpi, aa=True):
    with tempfile.TemporaryDirectory() as d:
        args = ["pdftoppm", "-r", str(dpi), "-gray", "-png", "-singlefile"]
        if not aa:
            args += ["-aa", "no", "-aaVector", "no"]
        subprocess.run(args + [pdf, f"{d}/p"], check=True)
        return cv2.imread(f"{d}/p.png", cv2.IMREAD_GRAYSCALE)


def crops(img, dpi):
    px = dpi / 25.4
    H = img.shape[0]
    for sid, x, y, rot in sheet.SLOTS:
        w, h = (40, 30) if rot in (0, 180) else (30, 40)
        x0, x1 = int(round(x * px)), int(round((x + w) * px))
        y0, y1 = int(round(H - (y + h) * px)), int(round(H - y * px))
        cr = img[y0:y1, x0:x1]
        if rot == 90:
            cr = cv2.rotate(cr, cv2.ROTATE_90_CLOCKWISE)
        yield sid, cr


def decode(det, cr):
    # margem branca + upscale leve ajudam o detector em recorte pequeno
    big = cv2.copyMakeBorder(cr, 40, 40, 40, 40, cv2.BORDER_CONSTANT, value=255)
    for scale in (1.0, 1.5, 2.0):
        im = cv2.resize(big, None, fx=scale, fy=scale, interpolation=cv2.INTER_NEAREST) if scale != 1 else big
        res = det.detectAndDecodeWithType(im) if hasattr(det, "detectAndDecodeWithType") else det.detectAndDecode(im)
        texts = [t for t in (res[1] if len(res) >= 2 else []) if t]
        if texts:
            return texts[0]
    return ""


def run(pdf, expected):
    w, h = page_size_mm(pdf)
    ok_size = abs(w - 100) < 0.01 and abs(h - 150) < 0.01
    print(f"\n{pdf.split('/')[-1]}  →  {w:.2f} × {h:.2f} mm  {'OK' if ok_size else 'ERRO'}")
    det = cv2.barcode.BarcodeDetector()
    allok = ok_size
    scenarios = [("300dpi jato/laser", 300, True, 0.8, False),
                 ("203dpi térmica", 203.2, False, 0.8, False),
                 ("térmica+ganho", 203.2, False, 1.6, True)]
    for name, dpi, aa, sigma, gain in scenarios:
        img = raster(pdf, dpi, aa)
        if not aa:
            _, img = cv2.threshold(img, 128, 255, cv2.THRESH_BINARY)
        if gain:
            # pontos físicos (×4), barra engorda 1 px a 4× = 0,031 mm por lado
            img = cv2.resize(img, None, fx=4, fy=4, interpolation=cv2.INTER_NEAREST)
            img = cv2.erode(img, np.ones((3, 3), np.uint8))
            img = cv2.GaussianBlur(img, (0, 0), sigma)
            img = cv2.resize(img, None, fx=0.5, fy=0.5, interpolation=cv2.INTER_AREA)
            dpi = dpi * 2
        else:
            img = cv2.GaussianBlur(img, (0, 0), sigma)
        got = 0
        fails = []
        for (sid, cr), d in zip(crops(img, dpi), expected):
            txt = decode(det, cr)
            if txt == d.ean:
                got += 1
            else:
                fails.append(f"{sid}:{txt or '—'}")
        allok &= got == len(expected)
        print(f"  {name:16s} {got}/{len(expected)} lidos" + (f"  falhas: {fails}" if fails else ""))
    return allok


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else "out"
    if len(sys.argv) >= 4:
        data = sheet.product_data(float(sys.argv[2].replace(",", ".")), sys.argv[3],
                                  sys.argv[4] if len(sys.argv) > 4 else None)
    else:
        data = sheet.demo_data()
    ok = True
    for t in ("PRETA", "TERMICA"):
        ok &= run(f"{out}/VC-Outlet_etiquetas-4x3_folha-10x15_{t}.pdf", data)
    print("\nRESULTADO:", "TUDO OK" if ok else "TEM FALHA")
