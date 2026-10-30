// test_recent.js — histórico de etiquetas: gravar ao imprimir, preencher pelo código, repetir folha, buscar.
const { chromium } = require("playwright");
const fs = require("fs"), path = require("path");
(async () => {
  const file = path.resolve(process.argv[2]), out = path.resolve(process.argv[3] || "t");
  const b = await chromium.launch(); const errors = [];
  const ctx = await b.newContext({ viewport: { width: 1280, height: 1200 }, colorScheme: "dark" });
  const page = await ctx.newPage();
  page.on("pageerror", e => errors.push(e.message));
  page.on("console", m => m.type() === "error" && errors.push(m.text()));
  await page.addInitScript(() => { window.print = () => { window.__printed = (window.__printed || 0) + 1; }; });
  await page.goto("file://" + file); await page.waitForTimeout(300);
  const log = {};
  const fields = () => page.evaluate(() => [...document.querySelectorAll(".item")].map(el => ({
    code: el.querySelector('[data-f="code"]').value, name: el.querySelector('[data-f="name"]').value,
    price: el.querySelector('[data-f="price"]').value, size: [...el.querySelectorAll('.chip[aria-pressed="true"]')].map(c => c.dataset.s)[0] || el.querySelector('[data-f="size"]').value,
    qty: el.querySelector('[data-f="qty"]').value, status: el.querySelector("[data-status]").innerText })));
  const H = () => page.evaluate(() => { const h = window.vcEtiquetas.hist(); return { catalog: h.catalog.map(c => `${c.ean}|${c.name}|${c.price}|${c.size}|${c.uses}`), jobs: h.jobs.map(j => `${j.n}:${j.products.length}`) }; });

  log.vazio = await page.evaluate(() => ({ open: document.querySelector("#recent").open, empty: !document.querySelector("#recEmpty").hidden }));

  // 1) nomeia e imprime a folha de exemplo → grava
  await page.locator('[data-f="name"]').first().fill("Camiseta oversized");
  await page.waitForTimeout(100);
  await page.click("#print");
  log.aposImprimir1 = await H();

  // 2) folha nova + passa o mesmo código → preenche sozinho
  await page.click("#clear"); await page.waitForTimeout(100);
  log.folhaNova = await fields();
  const code = page.locator('[data-f="code"]').first();
  await code.type("2787789328799"); await code.press("Enter");
  await page.waitForTimeout(100);
  log.autofill = await fields();
  log.focoAposEnter = await page.evaluate(() => document.activeElement.dataset.f);

  // 3) troca o código → desfaz o preenchimento automático
  await code.fill("1402"); await page.waitForTimeout(100);
  log.trocouCodigo = await fields();

  // 4) preenche outro produto e imprime → 2 no histórico
  await page.locator('[data-f="name"]').first().fill("Calça jeans");
  await page.locator('[data-f="price"]').first().fill("89,90");
  await page.locator('.chip[data-s="GG"]').first().click();
  await page.waitForTimeout(100);
  await page.click("#print");
  log.aposImprimir2 = await H();

  // 5) recarrega: recentes abertos
  await page.reload(); await page.waitForTimeout(300);
  log.recarregou = await page.evaluate(() => ({ open: document.querySelector("#recent").open, count: document.querySelector("#recCount").innerText,
    jobs: [...document.querySelectorAll(".job")].map(j => j.innerText.replace(/\n/g, " | ")),
    recs: [...document.querySelectorAll(".rec-main")].map(j => j.innerText.replace(/\n/g, " | ")) }));
  await page.screenshot({ path: `${out}/ui_recentes.png` });

  // 6) repetir a primeira folha (índice 1 = camiseta) e desfazer
  await page.click('.job[data-job="1"]'); await page.waitForTimeout(100);
  log.repetiu = await fields();
  await page.click("#undoBtn"); await page.waitForTimeout(100);
  log.desfez = await fields();

  // 7) folha nova + toca num produto recente
  await page.click("#clear"); await page.waitForTimeout(100);
  await page.click('.rec-main[data-rec="2787789328799"]'); await page.waitForTimeout(100);
  log.usouRecente = await fields();
  // adiciona o outro recente → vira 2º produto ocupando... (folha cheia → nova folha)
  await page.click('.rec-main[data-rec="2000000014029"]'); await page.waitForTimeout(100);
  log.doisRecentes = { f: await fields(), total: await page.evaluate(() => document.querySelector("#total").innerText.replace(/\n/g, " | ")) };

  // 8) usar o salvo quando o preço difere
  await page.locator('[data-f="price"]').first().fill("99,90"); await page.waitForTimeout(100);
  log.difere = (await fields())[0].status;
  await page.locator('[data-act="usesaved"]').first().click(); await page.waitForTimeout(100);
  log.usouSalvo = (await fields())[0];

  // 9) busca sem acento + remover dos recentes
  await page.fill("#recSearch", "calca"); await page.waitForTimeout(100);
  log.busca = await page.evaluate(() => [...document.querySelectorAll(".rec-main")].map(r => r.innerText.split("\n")[0]));
  await page.fill("#recSearch", ""); await page.waitForTimeout(50);
  await page.click('[data-recdel="2000000014029"]'); await page.waitForTimeout(50);
  log.removeu = await H();

  // celular
  const m = await b.newContext({ viewport: { width: 390, height: 844 }, colorScheme: "light", deviceScaleFactor: 2 });
  const mp = await m.newPage(); mp.on("pageerror", e => errors.push("mobile: " + e.message));
  await mp.goto("file://" + file); await mp.waitForTimeout(300);
  log.mobileOverflow = await mp.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
  log.errors = errors;
  console.log(JSON.stringify(log, null, 1));
  await b.close();
  const CHECKS = [
    ["grava ao imprimir", log.aposImprimir1.catalog.length === 1 && log.aposImprimir2.catalog.length === 2],
    ["preenche pelo código", log.autofill[0].name === "Camiseta oversized" && log.autofill[0].price === "119,99" && log.autofill[0].size === "G"],
    ["desfaz ao trocar o código", log.trocouCodigo[0].name === "" && log.trocouCodigo[0].price === ""],
    ["recentes abertos depois de recarregar", log.recarregou.open && log.recarregou.recs.length === 2],
    ["repetir folha", log.repetiu[0].name === "Camiseta oversized"],
    ["usar o salvo", log.usouSalvo.price === "119,99"],
    ["busca sem acento", JSON.stringify(log.busca) === JSON.stringify(["CALÇA JEANS"])],
    ["sem rolagem lateral no celular", log.mobileOverflow === 0],
    ["sem erros de JS", errors.length === 0],
  ];
  const fails = CHECKS.filter(([, ok]) => !ok).map(([n]) => n);
  if (fails.length) { console.error("FALHOU:", fails.join(", ")); process.exitCode = 1; }
})().catch(e => { console.error(e); process.exit(1); });
