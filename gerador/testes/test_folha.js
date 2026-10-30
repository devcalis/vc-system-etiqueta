// test3.js — fluxo "trocar só algumas etiquetas da folha" + regressões.
const { chromium } = require("playwright");
const fs = require("fs");
const path = require("path");

(async () => {
  const file = path.resolve(process.argv[2]);
  const out = path.resolve(process.argv[3] || "t");
  fs.mkdirSync(out, { recursive: true });
  const browser = await chromium.launch();
  const errors = [];
  const ctx = await browser.newContext({ viewport: { width: 1280, height: 1100 }, colorScheme: "dark" });
  const page = await ctx.newPage();
  page.on("pageerror", e => errors.push("pageerror: " + e.message));
  page.on("console", m => { if (m.type() === "error") errors.push("console: " + m.text()); });
  await page.goto("file://" + file);
  await page.waitForTimeout(300);
  const pdf = async name => {
    const b64 = await page.evaluate(async () => {
      const u = await window.vcEtiquetas.buildPDF();
      let s = ""; for (let i = 0; i < u.length; i += 0x8000) s += String.fromCharCode.apply(null, u.subarray(i, i + 0x8000));
      return btoa(s);
    });
    fs.writeFileSync(`${out}/${name}`, Buffer.from(b64, "base64"));
  };
  const snap = () => page.evaluate(() => ({
    slots: window.vcEtiquetas.state.slots.map(v => v == null ? null : window.vcEtiquetas.state.products.findIndex(p => p.id === v) + 1),
    qty: [...document.querySelectorAll('[data-f="qty"]')].map(i => i.value),
    sums: [...document.querySelectorAll("[data-sum]")].map(s => s.innerText),
    total: document.querySelector("#total").innerText.replace(/\n/g, " | "),
    dl: !document.querySelector("#download").disabled,
  }));
  const log = {};
  log.inicio = await snap();

  // 1) seleciona as etiquetas 1, 2 e 6 da folha e troca por um produto novo
  for (const n of [0, 1, 5]) { await page.click(`.slot[data-slot="${n}"]`); await page.waitForTimeout(60); }
  log.painel = await page.evaluate(() => ({ visible: !document.querySelector("#selPanel").hidden, txt: document.querySelector("#selCount").innerText,
    opts: [...document.querySelectorAll("#selOpts button")].map(b => b.innerText) }));
  await page.screenshot({ path: `${out}/ui_selecao.png` });
  await page.click('#selOpts [data-assign="new"]');
  await page.waitForTimeout(150);
  log.foco = await page.evaluate(() => ({ f: document.activeElement.dataset.f, id: document.activeElement.id }));
  await page.keyboard.type("1402");
  await page.keyboard.press("Enter");
  await page.keyboard.type("89,9");
  await page.keyboard.press("Tab");
  await page.locator('.item').nth(1).locator('.chip[data-s="GG"]').click();
  await page.waitForTimeout(150);
  log.depoisTroca = await snap();
  await page.screenshot({ path: `${out}/ui_trocadas.png` });
  await pdf("t6_troca3.pdf");

  // 2) deixa a etiqueta 12 vazia
  await page.click('.slot[data-slot="11"]');
  await page.click('#selOpts [data-assign="none"]');
  await page.waitForTimeout(100);
  log.vazia = await snap();
  await pdf("t6_vazia.pdf");

  // 3) "+" no produto 2 ocupa a posição vazia
  await page.locator('.item').nth(1).locator('[data-act="inc"]').click();
  await page.waitForTimeout(100);
  log.preencheu = await snap();

  // 4) quantidade 20 no produto 1 → abre folha 2
  const q1 = page.locator('[data-f="qty"]').first();
  await q1.fill("20"); await q1.press("Tab");
  await page.waitForTimeout(100);
  log.duasFolhas = await snap();
  // seleciona 2 etiquetas na folha 2 e passa pro produto 2
  await page.click("#next");
  await page.click('.slot[data-slot="12"]');
  await page.click('.slot[data-slot="13"]');
  await page.click('#selOpts button[data-assign]:nth-child(3)'); // Produto 2
  await page.waitForTimeout(100);
  log.folha2 = await snap();
  await pdf("t6_duas.pdf");

  // 5) remover produto 2 e desfazer
  await page.locator('.item').nth(1).locator('[data-act="remove"]').click();
  await page.waitForTimeout(100);
  log.removido = await snap();
  await page.click("#undoBtn");
  await page.waitForTimeout(100);
  log.desfeito = await snap();

  // 6) recarrega: estado salvo
  await page.waitForTimeout(400); await page.reload(); await page.waitForTimeout(300);
  log.recarregado = await snap();
  await page.screenshot({ path: `${out}/ui_final.png`, fullPage: true });

  // celular
  const m = await browser.newContext({ viewport: { width: 390, height: 844 }, colorScheme: "light", deviceScaleFactor: 2 });
  const mp = await m.newPage();
  mp.on("pageerror", e => errors.push("mobile: " + e.message));
  await mp.goto("file://" + file); await mp.waitForTimeout(300);
  await mp.click('.slot[data-slot="2"]'); await mp.click('.slot[data-slot="3"]');
  log.mobileOverflow = await mp.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
  await mp.locator(".c-sheet").screenshot({ path: `${out}/ui_mobile_sheet.png` });

  log.errors = errors;
  fs.writeFileSync(`${out}/t6_log.json`, JSON.stringify(log, null, 1));
  await browser.close();
  console.log(JSON.stringify(log, null, 1));
  const eq = (a, b) => JSON.stringify(a) === JSON.stringify(b);
  const CHECKS = [
    ["troca de 3 etiquetas", eq(log.depoisTroca.slots, [2, 2, 1, 1, 1, 2, 1, 1, 1, 1, 1, 1])],
    ["posição vazia", eq(log.vazia.slots, [2, 2, 1, 1, 1, 2, 1, 1, 1, 1, 1, null])],
    ["+ preenche a vazia", eq(log.preencheu.slots, [2, 2, 1, 1, 1, 2, 1, 1, 1, 1, 1, 2])],
    ["desfazer remoção", eq(log.desfeito.slots, log.folha2.slots)],
    ["estado salvo ao recarregar", eq(log.recarregado.slots, log.desfeito.slots)],
    ["sem rolagem lateral no celular", log.mobileOverflow === 0],
    ["sem erros de JS", errors.length === 0],
  ];
  const fails = CHECKS.filter(([, ok]) => !ok).map(([n]) => n);
  if (fails.length) { console.error("FALHOU:", fails.join(", ")); process.exitCode = 1; }
})().catch(e => { console.error(e); process.exit(1); });
