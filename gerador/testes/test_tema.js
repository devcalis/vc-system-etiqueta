// test_tema.js — etiqueta Preta / Branca: troca, PDF, salva ao recarregar, histórico guarda a cor.
const { chromium } = require("playwright");
const fs = require("fs"), path = require("path");
(async () => {
  const file = path.resolve(process.argv[2]), out = path.resolve(process.argv[3] || "t");
  fs.mkdirSync(out, { recursive: true });
  const b = await chromium.launch(); const errors = [];
  const page = await (await b.newContext({ viewport: { width: 1280, height: 1100 }, colorScheme: "light" })).newPage();
  page.on("pageerror", e => errors.push(e.message));
  page.on("console", m => m.type() === "error" && errors.push(m.text()));
  await page.addInitScript(() => { window.print = () => {}; });
  await page.goto("file://" + file); await page.waitForTimeout(300);
  const pdf = async name => {
    const b64 = await page.evaluate(async () => { const u = await window.vcEtiquetas.buildPDF(); let s = ""; for (let i = 0; i < u.length; i += 0x8000) s += String.fromCharCode.apply(null, u.subarray(i, i + 0x8000)); return btoa(s); });
    fs.writeFileSync(`${out}/${name}`, Buffer.from(b64, "base64"));
  };
  const pressed = () => page.evaluate(() => [...document.querySelectorAll("[data-theme-pick]")].map(x => `${x.dataset.themePick}:${x.getAttribute("aria-pressed")}`).join(" "));
  const log = {};
  // produto com nome e uma etiqueta trocada (pra ter as duas variações na folha)
  await page.locator('[data-f="name"]').first().fill("Camiseta oversized");
  await page.click('.slot[data-slot="0"]'); await page.waitForTimeout(60);
  await page.click('#selOpts [data-assign="new"]'); await page.waitForTimeout(100);
  await page.keyboard.type("1402"); await page.keyboard.press("Enter"); await page.keyboard.press("Enter");
  await page.keyboard.type("89,90"); await page.keyboard.press("Tab"); await page.waitForTimeout(100);

  log.inicio = await pressed();
  await pdf("t8_preta.pdf");
  await page.click('[data-theme-pick="branca"]'); await page.waitForTimeout(150);
  log.branca = await pressed();
  log.labelBg = await page.evaluate(() => document.querySelector("#labelPreview path").getAttribute("fill"));
  await page.locator(".c-label").screenshot({ path: `${out}/ui_branca_label.png` });
  await page.locator(".c-sheet").screenshot({ path: `${out}/ui_branca_folha.png` });
  await pdf("t8_branca.pdf");
  await page.click("#print");                     // grava no histórico com a cor branca
  await page.waitForTimeout(400);
  await page.reload(); await page.waitForTimeout(300);
  log.recarregou = await pressed();
  log.job = await page.evaluate(() => document.querySelector(".job span").innerText);
  await page.click('[data-theme-pick="preta"]'); await page.waitForTimeout(100);
  await page.click('.job[data-job="0"]'); await page.waitForTimeout(150);
  log.repetiuFolha = await pressed();
  await page.click("#undoBtn"); await page.waitForTimeout(100);
  log.desfez = await pressed();
  await page.screenshot({ path: `${out}/ui_branca_tela.png` });

  console.log(JSON.stringify({ ...log, errors }, null, 1));
  await b.close();
  const CHECKS = [
    ["começa na preta", log.inicio === "preta:true branca:false"],
    ["troca pra branca", log.branca === "preta:false branca:true" && log.labelBg === "#FFFFFF"],
    ["lembra a cor ao recarregar", log.recarregou === "preta:false branca:true"],
    ["histórico mostra a cor", /branca/.test(log.job)],
    ["repetir folha volta a cor", log.repetiuFolha === "preta:false branca:true"],
    ["desfazer volta a cor", log.desfez === "preta:true branca:false"],
    ["sem erros de JS", errors.length === 0],
  ];
  const fails = CHECKS.filter(([, ok]) => !ok).map(([n]) => n);
  if (fails.length) { console.error("FALHOU:", fails.join(", ")); process.exitCode = 1; }
})().catch(e => { console.error(e); process.exit(1); });
