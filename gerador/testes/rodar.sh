#!/usr/bin/env bash
# Roda todos os testes do gerador: monta o index.html, exercita a página no Chromium
# (Playwright) e confere os PDFs gerados (tamanho e leitura dos códigos de barras).
set -euo pipefail
cd "$(dirname "$0")"
OUT=saida
mkdir -p "$OUT"
python3 ../build.py
for t in test_folha test_nome test_recentes test_impressao test_tema test_promo; do
  printf '▶ %-16s ' "$t"
  node "$t.js" ../../index.html "$OUT" > "$OUT/$t.log" 2>&1 && echo "ok" || { echo "FALHOU (veja $OUT/$t.log)"; exit 1; }
done
python3 verifica_pdfs.py "$OUT"
