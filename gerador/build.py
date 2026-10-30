"""
build.py — monta o gerador final a partir do código-fonte.

Entrada:
  gerador/gerador.src.html   página (HTML + CSS + JS), com o marcador /*__ASSETS__*/null
  etiqueta/assets.json       logo + contornos das fontes (gerado por etiqueta/export_assets.py)

Saída:
  index.html                       documento completo, abre direto no navegador (tem o botão Imprimir)
  gerador/dist/claude-artifact.html  só o corpo da página, no formato que o claude.ai publica

uso: python3 gerador/build.py
"""
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

src = open(os.path.join(HERE, "gerador.src.html"), encoding="utf-8").read()
assets = open(os.path.join(ROOT, "etiqueta", "assets.json"), encoding="utf-8").read()
assert "/*__ASSETS__*/null" in src, "marcador /*__ASSETS__*/null não encontrado no gerador.src.html"
body = src.replace("/*__ASSETS__*/null", assets)

# claude.ai: o próprio claude.ai envolve a página com <!doctype>, <head> e <body>
os.makedirs(os.path.join(HERE, "dist"), exist_ok=True)
frag = os.path.join(HERE, "dist", "claude-artifact.html")
open(frag, "w", encoding="utf-8").write(body)

# navegador: documento completo (charset é obrigatório quando abre como arquivo, file://)
page = ("<!doctype html><html lang=\"pt-BR\"><head><meta charset=\"utf-8\">"
        "<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">"
        "<style>body{margin:0}img{max-width:100%}[hidden]{display:none!important}</style>"
        "</head><body>" + body + "</body></html>")
index = os.path.join(ROOT, "index.html")
open(index, "w", encoding="utf-8").write(page)

for p in (index, frag):
    print(f"{os.path.relpath(p, ROOT)}  {os.path.getsize(p) // 1024} KB")
