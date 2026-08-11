function normalizeSpaces(value) {
  return String(value || '').replace(/\s+/g, ' ').trim();
}

function parsePriceText(text) {
  const normalized = normalizeSpaces(text)
    .replace(/₽/g, ' ₽')
    .replace(/\s+/g, ' ')
    .trim();

  const match = normalized.match(/(?:от\s*)?(\d[\d\s.,]{0,12})\s*₽/i);
  if (!match) return null;

  const numeric = match[1].replace(/[^\d]/g, '');
  if (!numeric) return null;

  const value = Number(numeric);
  if (!Number.isFinite(value) || value <= 0) return null;

  return {
    value,
    currency: 'RUB',
    text: `${value.toLocaleString('ru-RU')} ₽`
  };
}

function extractProductId(url = '') {
  const decoded = decodeURIComponent(String(url));
  const matches = [...decoded.matchAll(/(?:^|[-/])(\d{7,13})(?:[/?#]|$)/g)];
  return matches.length ? matches[matches.length - 1][1] : null;
}

function getElementDepth(element) {
  let depth = 0;
  let current = element;
  while (current?.parentElement) {
    depth += 1;
    current = current.parentElement;
  }
  return depth;
}

function visibleRect(element) {
  const rect = element.getBoundingClientRect();
  const style = window.getComputedStyle(element);
  if (
    rect.width <= 0 ||
    rect.height <= 0 ||
    style.visibility === 'hidden' ||
    style.display === 'none' ||
    Number(style.opacity) === 0
  ) {
    return null;
  }
  return {
    x: rect.x,
    y: rect.y,
    width: rect.width,
    height: rect.height,
    top: rect.top,
    right: rect.right,
    bottom: rect.bottom,
    left: rect.left
  };
}

function isLineThrough(element) {
  let current = element;
  while (current && current !== document.body) {
    const style = window.getComputedStyle(current);
    if (style.textDecorationLine?.includes('line-through')) return true;
    current = current.parentElement;
  }
  return false;
}

function directText(element) {
  return [...element.childNodes]
    .filter((node) => node.nodeType === Node.TEXT_NODE)
    .map((node) => node.textContent)
    .join(' ')
    .replace(/\s+/g, ' ')
    .trim();
}

function elementText(element) {
  return String(element?.textContent || '').replace(/\s+/g, ' ').trim();
}

function nearestText(element, levels = 4) {
  let current = element;
  const parts = [];
  for (let i = 0; i < levels && current; i += 1) {
    parts.push(elementText(current));
    current = current.parentElement;
  }
  return parts.join(' ');
}

function nearestAncestor(element, predicate, maxDepth = 10) {
  let current = element;
  for (let i = 0; i < maxDepth && current && current !== document.body; i += 1) {
    if (predicate(current)) return current;
    current = current.parentElement;
  }
  return null;
}

function hasOzonBankPriceLabel(text) {
  const lower = normalizeSpaces(text).toLowerCase();
  return /(?:\u0441\s+\u0431\u0430\u043d\u043a\u0430\u043c\u0438|\u0441\s+ozon|ozon\s+\u0431\u0430\u043d\u043a|\u043a\u0430\u0440\u0442(?:\u043e\u0439|\u0430)\s+ozon)/i.test(lower);
}

function detailCandidateFromElement(element, baseScore, baseReason) {
  const rawText = elementText(element);
  if (!rawText || !/\d/.test(rawText) || !hasOzonBankPriceLabel(rawText)) return null;

  const price = parsePriceText(rawText);
  if (!price) return null;

  const rect = visibleRect(element);
  if (!rect) return null;

  const style = window.getComputedStyle(element);
  const context = nearestText(element, 5);
  const lineThrough = isLineThrough(element);
  const fontSize = Number.parseFloat(style.fontSize || '0') || 0;
  const fontWeight = Number.parseInt(style.fontWeight || '400', 10) || 400;
  const vw = window.innerWidth || 1440;
  const vh = window.innerHeight || 900;
  const reasons = [baseReason];
  let score = baseScore;

  if (lineThrough) {
    score -= 100;
    reasons.push('excluded-line-through');
  }

  if (element.closest('[data-widget="webPrice"]')) {
    score += 30;
    reasons.push('web-price-widget');
  }

  if (element.matches('button, [role="button"]') || element.closest('button, [role="button"]')) {
    score += 18;
    reasons.push('bank-price-button');
  }

  if (rect.left > vw * 0.55) {
    score += 12;
    reasons.push('right-buy-column');
  }

  if (rect.top > vh * 0.12 && rect.top < vh * 0.7) {
    score += 8;
    reasons.push('visible-buy-card-zone');
  }

  return {
    price,
    rawText,
    context: context.slice(0, 800),
    rect,
    lineThrough,
    fontSize,
    fontWeight,
    depth: getElementDepth(element),
    tagName: element.tagName.toLowerCase(),
    className: String(element.className || '').slice(0, 200),
    score,
    reasons
  };
}

function findDetailBankPriceCandidates() {
  const elements = [
    ...document.querySelectorAll('[data-widget="webPrice"], [data-widget="webPrice"] button, [data-widget="webSale"] button, button, [role="button"]')
  ];
  const seen = new Set();
  const candidates = [];

  for (const element of elements) {
    if (seen.has(element)) continue;
    seen.add(element);

    const candidate = detailCandidateFromElement(element, 95, 'bank-price-label');
    if (candidate && candidate.score > 0) candidates.push(candidate);
  }

  return candidates.sort((a, b) => b.score - a.score);
}

function collectPriceCandidates(root = document.body) {
  const candidates = [];
  const all = [...root.querySelectorAll('span, div, button, a, p')];

  for (const element of all) {
    const text = directText(element) || elementText(element);
    if (!text || !/[₽Р]/i.test(text) || !/\d/.test(text)) continue;

    const price = parsePriceText(text);
    if (!price) continue;

    const rect = visibleRect(element);
    if (!rect) continue;

    const style = window.getComputedStyle(element);
    const context = nearestText(element, 5);
    const lineThrough = isLineThrough(element);
    const fontSize = Number.parseFloat(style.fontSize || '0') || 0;
    const fontWeight = Number.parseInt(style.fontWeight || '400', 10) || 400;

    candidates.push({
      price,
      rawText: text,
      context: context.slice(0, 800),
      rect,
      lineThrough,
      fontSize,
      fontWeight,
      depth: getElementDepth(element),
      tagName: element.tagName.toLowerCase(),
      className: String(element.className || '').slice(0, 200)
    });
  }

  return candidates;
}

function scoreDetailCandidate(candidate) {
  const vw = window.innerWidth || 1440;
  const vh = window.innerHeight || 900;
  const context = candidate.context.toLowerCase();
  let score = 0;
  const reasons = [];

  if (candidate.lineThrough) {
    score -= 100;
    reasons.push('excluded-line-through');
  }

  if (candidate.rect.left > vw * 0.55) {
    score += 35;
    reasons.push('right-buy-column');
  }

  if (candidate.rect.top > vh * 0.18 && candidate.rect.top < vh * 0.58) {
    score += 18;
    reasons.push('top-buy-card-zone');
  }

  if (/в корзину|купить сейчас|без переплат|стало дешевле|с банками|оплатить позже/.test(context)) {
    score += 35;
    reasons.push('buy-card-context');
  }

  if (/другими банками|ozon банк|ozon card|картой/.test(context)) {
    score += 18;
    reasons.push('green-price-neighbor-text');
  }

  if (candidate.fontSize >= 24) {
    score += 24;
    reasons.push('large-price-font');
  } else if (candidate.fontSize >= 18) {
    score += 12;
    reasons.push('medium-price-font');
  }

  if (candidate.fontWeight >= 600) {
    score += 10;
    reasons.push('bold-price');
  }

  if (/от\s+\d/.test(candidate.rawText.toLowerCase())) {
    score -= 20;
    reasons.push('from-price-penalty');
  }

  return { score, reasons };
}

function findDetailGreenPrice() {
  const bankPriceCandidates = findDetailBankPriceCandidates();
  const scannedCandidates = collectPriceCandidates()
    .map((candidate) => {
      const scored = scoreDetailCandidate(candidate);
      return { ...candidate, ...scored };
    })
    .filter((candidate) => candidate.score > 0);

  const candidates = [...bankPriceCandidates, ...scannedCandidates]
    .sort((a, b) => b.score - a.score);

  const best = candidates[0] || null;
  const productId = extractProductId(location.href);
  const title =
    elementText(document.querySelector('h1')) ||
    document.title.replace(/\s+купить.+$/i, '').trim();

  return {
    pageType: 'detail',
    productId,
    url: location.href,
    title,
    price: best?.price || null,
    confidence: best ? Math.min(0.99, Math.max(0.25, best.score / 130)) : 0,
    rawText: best?.rawText || '',
    reason: best?.reasons?.join(', ') || 'no-price-candidate',
    candidates: candidates.slice(0, 8).map((candidate) => ({
      price: candidate.price,
      rawText: candidate.rawText,
      score: candidate.score,
      reason: candidate.reasons.join(', '),
      rect: candidate.rect,
      lineThrough: candidate.lineThrough,
      fontSize: candidate.fontSize
    }))
  };
}

function linkToAbsoluteUrl(link) {
  if (!link) return '';
  try {
    return new URL(link.getAttribute('href'), location.href).href;
  } catch {
    return link.href || '';
  }
}

function findProductCard(link) {
  return nearestAncestor(
    link,
    (element) => {
      const text = elementText(element).toLowerCase();
      const rect = visibleRect(element);
      if (!rect) return false;
      if (rect.width < 120 || rect.height < 160) return false;
      if (!/[₽Р]/i.test(text)) return false;
      if (!text.includes('в корзину') && !text.includes('отзыв') && !text.includes('достав')) {
        return false;
      }
      return element.querySelector('a[href*="/product/"]');
    },
    9
  );
}

function scoreSearchCandidate(candidate, cardRect) {
  let score = 0;
  const reasons = [];
  const yRatio = (candidate.rect.top - cardRect.top) / Math.max(1, cardRect.height);
  const xInside = candidate.rect.left >= cardRect.left - 8 && candidate.rect.right <= cardRect.right + 8;
  const context = candidate.context.toLowerCase();

  if (!xInside) {
    score -= 35;
    reasons.push('outside-card-x');
  }

  if (candidate.lineThrough) {
    score -= 100;
    reasons.push('excluded-line-through');
  }

  if (yRatio > 0.34 && yRatio < 0.74) {
    score += 30;
    reasons.push('below-image-above-actions-zone');
  }

  if (candidate.fontSize >= 22) {
    score += 24;
    reasons.push('large-card-price');
  } else if (candidate.fontSize >= 17) {
    score += 14;
    reasons.push('medium-card-price');
  }

  if (candidate.fontWeight >= 600) {
    score += 10;
    reasons.push('bold-card-price');
  }

  if (/распродажа|цена что надо|стало дешевле|осталось|остался|шт осталось/.test(context)) {
    score += 12;
    reasons.push('promo-neighbor');
  }

  if (/отзыв|рейтинг|sku|продавец|бренд|месяц|дней|продаж/.test(candidate.rawText.toLowerCase())) {
    score -= 20;
    reasons.push('metric-text-penalty');
  }

  return { score, reasons };
}

function getTitleFromCard(card, productUrl) {
  const links = [...card.querySelectorAll('a[href*="/product/"]')];
  const textLinks = links
    .map((link) => elementText(link))
    .filter((text) => text.length > 8 && !/[₽Р]/i.test(text))
    .sort((a, b) => b.length - a.length);
  if (textLinks[0]) return textLinks[0].slice(0, 240);

  const urlSlug = productUrl.split('/product/')[1]?.split('/')[0] || '';
  return decodeURIComponent(urlSlug).replace(/-/g, ' ').slice(0, 240);
}

function findSearchGreenPrices() {
  const links = [...document.querySelectorAll('a[href*="/product/"]')];
  const seenCards = new Set();
  const products = [];

  for (const link of links) {
    const productUrl = linkToAbsoluteUrl(link);
    const productId = extractProductId(productUrl);
    if (!productId) continue;

    const card = findProductCard(link);
    if (!card || seenCards.has(card)) continue;
    seenCards.add(card);

    const cardRect = visibleRect(card);
    if (!cardRect) continue;

    const candidates = collectPriceCandidates(card)
      .map((candidate) => {
        const scored = scoreSearchCandidate(candidate, cardRect);
        return { ...candidate, ...scored };
      })
      .filter((candidate) => candidate.score > 0)
      .sort((a, b) => b.score - a.score);

    const best = candidates[0] || null;

    products.push({
      pageType: 'search',
      productId,
      url: productUrl,
      title: getTitleFromCard(card, productUrl),
      price: best?.price || null,
      confidence: best ? Math.min(0.99, Math.max(0.25, best.score / 100)) : 0,
      rawText: best?.rawText || '',
      reason: best?.reasons?.join(', ') || 'no-card-price-candidate',
      cardRect,
      candidates: candidates.slice(0, 4).map((candidate) => ({
        price: candidate.price,
        rawText: candidate.rawText,
        score: candidate.score,
        reason: candidate.reasons.join(', '),
        rect: candidate.rect,
        lineThrough: candidate.lineThrough,
        fontSize: candidate.fontSize
      }))
    });
  }

  return {
    pageType: 'search',
    url: location.href,
    count: products.length,
    products
  };
}

export function extractOzonGreenPrices(pageType = 'auto') {
  const mode =
    pageType === 'auto'
      ? location.href.includes('/product/')
        ? 'detail'
        : 'search'
      : pageType;

  if (mode === 'detail') return findDetailGreenPrice();
  return findSearchGreenPrices();
}
