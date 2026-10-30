// test_name.js — campo de nome: fluxo leitor → nome → preço, nomes curto/longo/acento, PDF.
const { chromium } = require("playwright");
const fs = require("fs"), path = require("path");
(async () => {
  const file = path.resolve(process.argv[2]), out = path.resolve(process.argv[3] || "t");
  const b = await chromium.launch(); const errors = [];
  const page = await (await b.newContext({ viewport: { width: 1280, height: 1100 }, colorScheme: "dark" })).newPage();
  page.on("pageerror", e => errors.push(e.message));
  await page.goto("file://" + file); await page.waitForTimeout(300);
  const code = page.locator('[data-f="code"]').first();
  await code.fill(""); await code.type("2787789328799"); await code.press("Enter");
  const f1 = await page.evaluate(() => document.activeElement.dataset.f);
  await page.keyboard.type("Camiseta oversized algodão");
  await page.keyboard.press("Enter");
  const f2 = await page.evaluate(() => document.activeElement.dataset.f);
  await page.keyboard.type("119,99"); await page.keyboard.press("Tab");
  // 3 etiquetas viram outro produto com nome longo
  for (const n of [0, 1, 5]) { await page.click(`.slot[data-slot="${n}"]`); await page.waitForTimeout(60); }
  await page.click('#selOpts [data-assign="new"]'); await page.waitForTimeout(100);
  await page.keyboard.type("1402"); await page.keyboard.press("Enter");
  await page.keyboard.press("Control+A");
  await page.keyboard.type("Calça jeans wide leg lavagem média escura");
  await page.keyboard.press("Enter");
  await page.keyboard.type("1.049,90"); await page.keyboard.press("Tab");
  await page.waitForTimeout(200);
  const info = await page.evaluate(() => ({
    titles: [...document.querySelectorAll("[data-title]")].map(e => e.innerText),
    who: document.querySelector("#labelWho").innerText,
    names: window.vcEtiquetas.state.products.map(p => p.name),
  }));
  await page.screenshot({ path: `${out}/ui_nome.png` });
  await page.locator(".label-mat").screenshot({ path: `${out}/ui_nome_label_longo.png` });
  await page.locator(".item").first().click({ position: { x: 20, y: 20 } });
  await page.locator('[data-f="name"]').first().focus(); await page.waitForTimeout(150);
  await page.locator(".label-mat").screenshot({ path: `${out}/ui_nome_label.png` });
  const b64 = await page.evaluate(async () => { const u = await window.vcEtiquetas.buildPDF(); let s = ""; for (let i = 0; i < u.length; i += 0x8000) s += String.fromCharCode.apply(null, u.subarray(i, i + 0x8000)); return btoa(s); });
  fs.writeFileSync(`${out}/t7_nome.pdf`, Buffer.from(b64, "base64"));
  console.log(JSON.stringify({ f1, f2, ...info, errors }, null, 1));
  const CHECKS = [
    ["Enter no código vai pro nome", f1 === "name"],
    ["Enter no nome vai pro preço", f2 === "price"],
    ["nome com acento em maiúsculas", info.titles[0] === "1. CAMISETA OVERSIZED ALGODÃO"],
    ["sem erros de JS", errors.length === 0],
  ];
  const fails = CHECKS.filter(([, ok]) => !ok).map(([n]) => n);
  if (fails.length) { console.error("FALHOU:", fails.join(", ")); process.exitCode = 1; }
  await b.close();
})().catch(e => { console.error(e); process.exit(1); });
