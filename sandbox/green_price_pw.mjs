/**
 * 绿标价抓取 — Playwright 版
 * 用法: node sandbox/green_price_pw.mjs
 * 前置: 先运行 python sandbox/dump_products.py 生成 products.json
 */
import { chromium } from 'playwright';
import { readFileSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';
import { homedir } from 'node:os';

import { fileURLToPath } from 'node:url';
const SANDBOX = fileURLToPath(new URL('.', import.meta.url));
const EXTRACTOR_JS = join(SANDBOX, 'ozon_dom_extractor.js');
const PRODUCTS_JSON = join(SANDBOX, 'products.json');
const OUTPUT = join(homedir(), 'Desktop', 'ozon_green_price_result.md');
const DELAY_MS = 15_000;

// ── 提取器 ──────────────────────────────────────
function loadExtractor() {
  let src = readFileSync(EXTRACTOR_JS, 'utf8');
  src = src.replace('export function extractOzonGreenPrices', 'function extractOzonGreenPrices');
  return src + '\nwindow.__extractOzonGreenPrices = extractOzonGreenPrices;\n';
}

// ── 抓单个 ──────────────────────────────────────
async function captureOne(page, extractorJs, skuId) {
  const url = `https://www.ozon.ru/product/${skuId}/`;
  try {
    await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 45_000 });
    await page.waitForTimeout(6_000);
    await page.mouse.wheel(0, 300);
    await page.waitForTimeout(500);
    await page.addScriptTag({ content: extractorJs });
    const data = await page.evaluate(() => window.__extractOzonGreenPrices('detail'));
    const price = data?.price;
    return {
      status: price ? 'ok' : 'not_found',
      price: price?.value || null,
      priceText: price?.text || null,
      confidence: data?.confidence || 0,
    };
  } catch (e) {
    return { status: 'error', price: null, priceText: null, confidence: 0, error: e.message };
  }
}

// ── 输出 md ─────────────────────────────────────
function writeMd(results) {
  const ok = results.filter(r => r.status === 'ok').length;
  const ts = new Date().toISOString().replace('T', ' ').slice(0, 19);
  const lines = [
    '# Ozon 绿标价 (Playwright)',
    '',
    `**时间**: ${ts}  |  **成功**: ${ok}  |  **总计**: ${results.length}`,
    '',
    '| # | offer_id | DB售价 | 绿标价 | MSP | 置信度 |',
    '|---|----------|-------:|------:|----:|------:|',
  ];
  for (let i = 0; i < results.length; i++) {
    const r = results[i];
    const db = r.db_price?.toLocaleString('ru-RU') || '—';
    const gr = (r.green_price_text || '—').replace(/\xa0/g, ' ');
    const msp = r.msp?.toLocaleString('ru-RU') || '—';
    const cf = r.confidence ? `${Math.round(r.confidence * 100)}%` : '—';
    lines.push(`| ${i+1} | [${r.offer_id}](${r.url}) | ${db} | **${gr}** | ${msp} | ${cf} |`);
  }
  lines.push('', '---', '*Playwright 无头 Chrome + 15s 间隔*');
  writeFileSync(OUTPUT, lines.join('\n'), 'utf8');
  return OUTPUT;
}

// ── main ────────────────────────────────────────
async function main() {
  const products = JSON.parse(readFileSync(PRODUCTS_JSON, 'utf8'));
  console.log(`共 ${products.length} 个商品\n`);

  // 用已下载的完整 Chromium (不用 headless shell，那个下载太慢)
  const chromiumPath = process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH || undefined;
  const browser = await chromium.launch({
    headless: true,
    executablePath: chromiumPath,
    args: ['--lang=ru-RU', '--no-sandbox', '--disable-blink-features=AutomationControlled'],
  });
  const context = await browser.newContext({
    locale: 'ru-RU',
    viewport: { width: 1440, height: 1100 },
    userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',
  });
  await context.addInitScript(() => {
    Object.defineProperty(navigator, 'webdriver', { get: () => false });
  });

  const extractorJs = loadExtractor();
  const results = [];

  for (let i = 0; i < products.length; i++) {
    const p = products[i];
    const url = `https://www.ozon.ru/product/${p.sku_id}/`;
    process.stdout.write(`[${i+1}/${products.length}] ${p.offer_id} ... `);

    const page = await context.newPage();
    const r = await captureOne(page, extractorJs, p.sku_id);
    await page.close();

    const pt = r.priceText || (r.price ? `${r.price.toLocaleString('ru-RU')} ₽` : null);
    console.log(`${pt || 'FAIL'}  (${r.status})`);

    results.push({ ...p, green_price: r.price, green_price_text: pt, status: r.status, confidence: r.confidence, url });

    if (i < products.length - 1) {
      await new Promise(res => setTimeout(res, DELAY_MS));
    }
  }

  await browser.close();
  const out = writeMd(results);
  console.log(`\n→ ${out}`);
}

main().catch(e => { console.error(e); process.exit(1); });
