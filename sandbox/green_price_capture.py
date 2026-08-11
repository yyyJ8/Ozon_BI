"""
绿标价抓取 — 用浏览器打开 Ozon 商品页，提取买家实际看到的价格
用法: python sandbox/green_price_capture.py [offer_id ...]
      python sandbox/green_price_capture.py 41634-Y07U0001-A01          # 单个
      python sandbox/green_price_capture.py --all --limit 10            # 前10个
      python sandbox/green_price_capture.py --all                       # 全部
"""
import json
import os
import sys
import tempfile
import time
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from DrissionPage import ChromiumOptions, ChromiumPage
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

load_dotenv()

# ── 跟项目相关的才写死，其他一律不硬编码 ──────────────
ROOT = Path(__file__).resolve().parent.parent
EXTRACTOR_JS = ROOT / "sandbox" / "ozon_dom_extractor.js"  # 提取器在我们自己项目里


# ═══════════════════════════════════════════════════════
#  浏览器
# ═══════════════════════════════════════════════════════

def _find_browser():
    """找 Chrome / Edge，优先注册表"""
    try:
        import winreg
        for subkey in [r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\chrome.exe",
                       r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\msedge.exe"]:
            for hive in [winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER]:
                try:
                    with winreg.OpenKey(hive, subkey) as k:
                        path, _ = winreg.QueryValueEx(k, "")
                        if path and Path(path).exists():
                            return path
                except OSError:
                    continue
    except Exception:
        pass
    # fallback: 常见路径
    for p in [r"C:\Program Files\Google\Chrome\Application\chrome.exe",
              r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
              os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
              r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
              r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
              os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\Edge\Application\msedge.exe")]:
        if Path(p).exists():
            return p
    raise FileNotFoundError("未找到 Chrome 或 Edge 浏览器")


def _create_browser():
    browser_path = _find_browser()
    profile = Path(tempfile.gettempdir()) / "ozon_green_price_profile"
    profile.mkdir(parents=True, exist_ok=True)

    opts = ChromiumOptions()
    opts.set_browser_path(browser_path)
    opts.set_user_data_path(str(profile))
    opts.set_load_mode("normal")
    opts.set_argument("--lang=ru-RU")
    opts.set_argument("--window-size=1440,1100")
    opts.set_argument("--no-first-run")
    opts.set_argument("--no-default-browser-check")
    if os.getenv("OZON_HEADLESS") == "1":
        opts.headless(True)

    return ChromiumPage(opts)


# ═══════════════════════════════════════════════════════
#  提取器 JS
# ═══════════════════════════════════════════════════════

def _load_extractor():
    """加载 ozon_dom_extractor.js，去掉 export 关键字供浏览器执行"""
    if not EXTRACTOR_JS.exists():
        raise FileNotFoundError(f"提取器 JS 不存在: {EXTRACTOR_JS}\n请从绿标价项目复制 ozon-dom-extractor.js 到此处")
    src = EXTRACTOR_JS.read_text(encoding="utf-8")
    src = src.replace("export function extractOzonGreenPrices",
                      "function extractOzonGreenPrices")
    return src + "\nwindow.__extractOzonGreenPrices = extractOzonGreenPrices;\n"


# ═══════════════════════════════════════════════════════
#  数据库 (只读)
# ═══════════════════════════════════════════════════════

def _get_db():
    db_url = (f"postgresql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}"
              f"@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}")
    return sessionmaker(bind=create_engine(db_url))()


def _fetch_products(db, offer_ids=None, limit=None):
    """取商品列表：指定 offer_id 或按 product_id 排序取前 N 个"""
    if offer_ids:
        rows = db.execute(
            text("""SELECT store_id, sku_id, product_id, name, offer_id, price, old_price,
                           marketing_seller_price
                    FROM ozon.products
                    WHERE offer_id = ANY(:ids) AND is_archived = false"""),
            {"ids": list(offer_ids)},
        ).fetchall()
    else:
        rows = db.execute(
            text("""SELECT store_id, sku_id, product_id, name, offer_id, price, old_price,
                           marketing_seller_price
                    FROM ozon.products
                    WHERE product_id IS NOT NULL AND is_archived = false
                    ORDER BY product_id
                    LIMIT :limit"""),
            {"limit": limit or 999999},
        ).fetchall()
    return rows


# ═══════════════════════════════════════════════════════
#  抓取
# ═══════════════════════════════════════════════════════

def capture_one(page, sku_id, extractor_js):
    """打开单个商品页，注入 JS 提取绿标价"""
    url = f"https://www.ozon.ru/product/{sku_id}/"

    try:
        page.get(url, timeout=45, show_errmsg=False)

        # 等页面渲染完
        deadline = time.time() + 15
        while time.time() < deadline:
            html = page.html or ""
            body = page.run_js(
                "return (document.body && document.body.innerText || '').slice(0, 5000);",
                timeout=3) or ""
            combined = (page.title + " " + body).lower()

            if any(kw in combined for kw in [
                "antibot captcha", "captcha-input", "abt-challenge",
                "похоже, нет", "access denied", "доступ ограничен",
            ]):
                return {"status": "blocked", "price": None, "rawText": "",
                        "error": "anti-bot"}

            if 'data-widget="webPrice"' in html or "С банками" in body or "₽" in body:
                break
            time.sleep(0.8)

        page.run_js("window.scrollBy(0, 300);", timeout=2)
        time.sleep(0.3)
        page.run_js("window.scrollTo(0, 0);", timeout=2)
        time.sleep(0.5)

        page.run_js(extractor_js, timeout=10)
        result = page.run_js(
            "return window.__extractOzonGreenPrices('detail');", timeout=15)

        if isinstance(result, dict):
            p = result.get("price")
            return {
                "status": "ok" if p else "not_found",
                "price": p.get("value") if p else None,
                "priceText": p.get("text") if p else None,
                "rawText": result.get("rawText", ""),
                "confidence": result.get("confidence", 0),
                "reason": result.get("reason", ""),
            }
        return {"status": "error", "price": None, "rawText": "",
                "error": "bad result type"}

    except Exception as e:
        return {"status": "error", "price": None, "rawText": "",
                "error": str(e)[:200]}


# ═══════════════════════════════════════════════════════
#  输出
# ═══════════════════════════════════════════════════════

def format_md(results, output_path):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines = [
        "# Ozon 绿标价查询结果",
        "",
        f"**抓取时间**: {ts}  |  **成功**: {sum(1 for r in results if r['status'] == 'ok')}  |  **被拦**: {sum(1 for r in results if r['status'] == 'blocked')}  |  **总计**: {len(results)}",
        "",
        "| # | offer_id | 商品链接 | DB售价 | 绿标价 | MSP | 置信度 | 状态 |",
        "|---|----------|----------|--------|--------|------|--------|------|",
    ]
    for i, r in enumerate(results, 1):
        db_p = f"{r['db_price']:,.0f}" if r['db_price'] else "—"
        # 清理 \xa0 不可断空格
        gr_p = (r['green_price_text'] or "—").replace('\xa0', ' ')
        msp_p = f"{r['marketing_seller_price']:,.0f}" if r.get('marketing_seller_price') else "—"
        conf = f"{r['confidence']:.0%}" if r.get('confidence') else "—"
        link = r['url']
        lines.append(
            f"| {i} | {r['offer_id']} | [打开]({link}) | {db_p} | {gr_p} | {msp_p} | {conf} | {r['status']} |"
        )

    lines.extend(["", "---",
                  "*绿标价 = 买家在商品页看到的 \"С банками\" 价格*"])
    output_path.write_text("\n".join(lines), encoding="utf-8")
    return output_path


# ═══════════════════════════════════════════════════════
#  main
# ═══════════════════════════════════════════════════════

def main():
    # 解析参数
    args = sys.argv[1:]
    offer_ids = None   # None = 从 DB 全量
    limit = None

    if "--all" in args:
        args.remove("--all")
    else:
        limit = 5  # 默认只取 5 个

    # --limit N
    for i, a in enumerate(args):
        if a == "--limit" and i + 1 < len(args):
            limit = int(args[i + 1])
            args.pop(i); args.pop(i)
            break

    # 剩余参数 = offer_id 列表
    if args:
        offer_ids = args
        limit = None

    # 1. 数据库
    db = _get_db()
    rows = _fetch_products(db, offer_ids, limit)
    db.close()
    if not rows:
        print("没有匹配的商品"); return
    print(f"共 {len(rows)} 个商品待抓取")

    # 2. 浏览器
    page = _create_browser()
    extractor_js = _load_extractor()

    # 3. 抓取
    results = []
    for i, row in enumerate(rows):
        _, sku, pid, name, oid, db_p, old_p, msp = row
        url = f"https://www.ozon.ru/product/{sku}/"
        print(f"[{i+1}/{len(rows)}] {oid} ... ", end="", flush=True)

        r = capture_one(page, sku, extractor_js)
        pt = r.get("priceText") or (f"{r['price']:,.0f} RUB" if r.get("price") else None)
        safe_pt = pt.replace('\xa0', ' ') if pt else None

        try:
            print(f"{safe_pt or 'FAIL'}  ({r['status']}, conf={r.get('confidence',0):.0%})")
        except UnicodeEncodeError:
            print(f"{r.get('price') or 'FAIL'}  ({r['status']})")

        results.append({
            "offer_id": oid, "sku_id": sku, "product_id": pid, "name": name,
            "db_price": float(db_p) if db_p else None,
            "old_price": float(old_p) if old_p else None,
            "marketing_seller_price": float(msp) if msp else None,
            "green_price": r.get("price"),
            "green_price_text": safe_pt,
            "status": r["status"],
            "confidence": r.get("confidence", 0),
            "url": url,
        })
        if i < len(rows) - 1:
            time.sleep(15)  # 模拟真人，避免 Ozon Anti-bot

    try: page.quit()
    except: pass

    # 4. 输出
    out = Path(os.getenv("GREEN_PRICE_OUTPUT",
                         str(Path.home() / "Desktop" / "ozon_green_price_result.md")))
    path = format_md(results, out)
    print(f"\n→ {path}")


if __name__ == "__main__":
    main()
