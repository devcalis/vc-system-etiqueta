// test_print.js — confere a impressão direta da versão do computador.
// Simula o "Imprimir": monta a área de impressão e gera o PDF que o Chrome mandaria pra impressora.
const { chromium } = require("playwright");
const fs = require("fs");
const path = require("path");

(async () => {
  const file = path.resolve(process.argv[2]);
  const out = path.resolve(process.argv[3] || "t");
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1280, height: 1000 }, colorScheme: "dark" });
  const errors = [];
  page.on("pageerror", e => errors.push(e.message));
  await page.goto("file://" + file);
  await page.waitForTimeout(300);

  const ui = await page.evaluate(() => ({
    title: document.title,
    printVisible: !document.querySelector("#print").hidden,
    tipVisible: !document.querySelector("#printTip").hidden,
    noteHidden: document.querySelector("#printNote").hidden,
    accents: document.querySelector(".help").innerText.slice(0, 60),
  }));

  // 2 produtos → 16 etiquetas → 2 folhas
  await page.evaluate(() => {
    const v = window.vcEtiquetas, s = v.state;
    v.setQty(s.products[0].id, 10);
    s.products.push({ id: 92, code: "1402", price: "89,90", size: "GG", generated: false });
    v.setQty(92, 6);
    v.renderItems(); v.renderPreview();
    window.print = () => { window.__printed = true; };   // não abre diálogo no headless
  });
  await page.waitForTimeout(150);
  await page.click("#print");
  const printed = await page.evaluate(() => ({ printed: !!window.__printed, pages: document.querySelectorAll("#printArea .pp").length }));
  await page.screenshot({ path: `${out}/ui_local_print.png` });

  await page.emulateMedia({ media: "print" });
  await page.pdf({ path: `${out}/t5_impressao.pdf`, preferCSSPageSize: true, printBackground: true });
  fs.writeFileSync(`${out}/t5_print.json`, JSON.stringify({ ui, printed, errors }, null, 1));
  await browser.close();
  console.log(JSON.stringify({ ui, printed, errors }));
  const CHECKS = [
    ["botão Imprimir aparece fora do claude.ai", ui.printVisible],
    ["uma página por folha", printed.printed && printed.pages === 2],
    ["sem erros de JS", errors.length === 0],
  ];
  const fails = CHECKS.filter(([, ok]) => !ok).map(([n]) => n);
  if (fails.length) { console.error("FALHOU:", fails.join(", ")); process.exitCode = 1; }
})().catch(e => { console.error(e); process.exit(1); });
