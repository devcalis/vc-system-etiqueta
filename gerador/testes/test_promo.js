// test_promo.js — preço promocional: riscado + selo, validação, histórico, PDF.
const { chromium } = require("playwright");
const fs = require("fs"), path = require("path");
(async () => {
  const file = path.resolve(process.argv[2]), out = path.resolve(process.argv[3] || "t");
  fs.mkdirSync(out, { recursive: true });
  const b = await chromium.launch(); const errors = [];
  const page = await (await b.newContext({ viewport: { width: 1280, height: 1150 }, colorScheme: "dark" })).newPage();
  page.on("pageerror", e => errors.push(e.message));
  page.on("console", m => m.type() === "error" && errors.push(m.text()));
  await page.addInitScript(() => { window.print = () => {}; });
  await page.goto("file://" + file); await page.waitForTimeout(300);
  const pdf = async name => {
    const b64 = await page.evaluate(async () => { const u = await window.vcEtiquetas.buildPDF(); let s = ""; for (let i = 0; i < u.length; i += 0x8000) s += String.fromCharCode.apply(null, u.subarray(i, i + 0x8000)); return btoa(s); });
    fs.writeFileSync(`${out}/${name}`, Buffer.from(b64, "base64"));
  };
  const card = n => page.evaluate(n => { const el = document.querySelectorAll(".item")[n]; return {
    promo: el.querySelector('[data-f="promo"]').value, info: el.querySelector("[data-promo]").innerText, kind: el.querySelector("[data-promo]").dataset.kind,
    status: el.querySelector("[data-status]").innerText, dl: !document.querySelector("#download").disabled, dlMsg: document.querySelector("#dlMsg").innerText }; }, n);
  const shot = async name => { await page.waitForTimeout(150); await page.locator(".label-mat svg").screenshot({ path: `${out}/${name}` }); };
  const log = {};
  const promo = page.locator('[data-f="promo"]').first();

  await shot("promo_0_sem.png");
  // 1) sem nome, 119,99 → 89,90
  await promo.fill("89,9"); await promo.press("Tab");
  log.valida = await card(0);
  await shot("promo_1_sem_nome.png");
  // 2) inválida: maior que o preço
  await promo.fill("150"); await page.waitForTimeout(100);
  log.maior = await card(0);
  await promo.fill("89,90"); await promo.press("Tab");
  // 3) com nome
  await page.locator('[data-f="name"]').first().fill("Camiseta oversized algodão");
  await shot("promo_2_com_nome.png");
  await pdf("t9_promo.pdf");
  // 4) preço de 4 dígitos + promoção de 4 dígitos
  await page.locator('[data-f="price"]').first().fill("1.299,90");
  await promo.fill("1.049,90"); await promo.press("Tab");
  await shot("promo_3_quatro_digitos.png");
  // 5) branca
  await page.click('[data-theme-pick="branca"]');
  await shot("promo_4_branca.png");
  await pdf("t9_promo_branca.pdf");
  await page.click('[data-theme-pick="preta"]');
  // 6) histórico: imprime, folha nova, passa o código → promoção NÃO entra sozinha, mas é oferecida
  await page.locator('[data-f="price"]').first().fill("119,99");
  await promo.fill("89,90"); await promo.press("Tab");
  await page.click("#print"); await page.waitForTimeout(100);
  log.rec = await page.evaluate(() => document.querySelector(".rec-meta").textContent);
  await page.click("#clear"); await page.waitForTimeout(100);
  const code = page.locator('[data-f="code"]').first();
  await code.type("2787789328799"); await page.waitForTimeout(150);
  log.autofill = await card(0);
  await page.locator('[data-act="usepromo"]').click(); await page.waitForTimeout(100);
  log.aplicou = await card(0);
  await page.screenshot({ path: `${out}/ui_promo.png` });

  console.log(JSON.stringify({ ...log, errors }, null, 1));
  await b.close();
  const CHECKS = [
    ["promoção válida mostra desconto", log.valida.promo === "89,90" && /−25%/.test(log.valida.info) && log.valida.dl],
    ["promoção maior que o preço bloqueia", /menor que o preço normal/.test(log.maior.info) && !log.maior.dl && /promoção/.test(log.maior.dlMsg)],
    ["recentes mostram a promoção", /89,90 \(de 119,99\)/.test(log.rec)],
    ["promoção não entra sozinha", log.autofill.promo === "" && /Aplicar a promoção de antes/.test(log.autofill.status)],
    ["aplicar promoção de antes", log.aplicou.promo === "89,90"],
    ["sem erros de JS", errors.length === 0],
  ];
  const fails = CHECKS.filter(([, ok]) => !ok).map(([n]) => n);
  if (fails.length) { console.error("FALHOU:", fails.join(", ")); process.exitCode = 1; }
})().catch(e => { console.error(e); process.exit(1); });
