"""
scraper_engine.py — 竞品数据采集引擎

双重模式:
  - 在线模式: Playwright/httpx 真实抓取竞品官网
  - 离线模式: 加载本地 fixture 缓存（面试demo用，网络不通也能跑）

架构:
  trigger_fetch(comp_id)
    → ScraperEngine.run(comp_id)
      → 尝试在线抓取 (Playwright 优先, httpx 兜底)
      → 成功: 保存 fixture → 返回 fetch_result
      → 失败: 加载 fixture → 返回 fetch_result
    → data_pipeline.run(comp_id, fetch_result)
"""
import json
import hashlib
import logging
import os
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

FIXTURES_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "fixtures"

# ── 各竞品的抓取目标配置 ──────────────────────────────────────
SCRAPER_TARGETS = {
    1: {
        "name": "阿里云",
        "urls": [
            "https://www.aliyun.com/product/list",
            "https://help.aliyun.com/zh/ecs/product-overview/instance-type-families",
        ],
        "selectors": {
            "product_cards": ".product-card, .product-item, [class*='product']",
            "product_name": "h1, h2, h3, .title, [class*='title']",
            "price_text": ".price, [class*='price'], [class*='Price']",
            "feature_list": ".feature, [class*='feature'], .tag, [class*='tag']",
        },
    },
    2: {
        "name": "腾讯云",
        "urls": [
            "https://cloud.tencent.com/product",
            "https://buy.cloud.tencent.com/pricing",
        ],
        "selectors": {
            "product_cards": ".product-card, .product-item, [class*='product']",
            "product_name": "h1, h2, h3, .title, [class*='title']",
            "price_text": ".price, [class*='price'], [class*='Price'], .cost",
            "feature_list": ".feature, [class*='feature'], .tag, [class*='tag']",
        },
    },
    3: {
        "name": "华为云",
        "urls": [
            "https://www.huaweicloud.com/product/",
            "https://www.huaweicloud.com/pricing.html",
        ],
        "selectors": {
            "product_cards": ".product-card, .product-item, [class*='product'], .card",
            "product_name": "h1, h2, h3, .title, [class*='title'], .card-title",
            "price_text": ".price, [class*='price'], [class*='Price'], .amount",
            "feature_list": ".feature, [class*='feature'], .tag, [class*='tag'], .badge",
        },
    },
    4: {
        "name": "AWS 中国",
        "urls": [
            "https://www.amazonaws.cn/products/",
            "https://www.amazonaws.cn/ec2/pricing/",
        ],
        "selectors": {
            "product_cards": ".product-card, .product-item, [class*='product'], .lb-card",
            "product_name": "h1, h2, h3, .title, [class*='title'], .lb-title",
            "price_text": ".price, [class*='price'], [class*='Price'], .lb-price",
            "feature_list": ".feature, [class*='feature'], .tag, [class*='tag'], .lb-feature",
        },
    },
    5: {
        "name": "百度 AI 云",
        "urls": [
            "https://cloud.baidu.com/product-list.html",
            "https://cloud.baidu.com/product/wenxinworkshop.html",
        ],
        "selectors": {
            "product_cards": ".product-card, .product-item, [class*='product'], .service-card",
            "product_name": "h1, h2, h3, .title, [class*='title'], .service-title",
            "price_text": ".price, [class*='price'], [class*='Price'], .fee, .cost",
            "feature_list": ".feature, [class*='feature'], .tag, [class*='tag'], .label",
        },
    },
}


class ScraperEngine:
    """竞品数据采集引擎"""

    def __init__(self, use_fixtures: bool = None):
        if use_fixtures is None:
            use_fixtures = os.getenv("SCRAPER_MODE", "online") == "fixtures"
        self._use_fixtures = use_fixtures
        FIXTURES_DIR.mkdir(parents=True, exist_ok=True)

    def run(self, competitor_id: int) -> Dict:
        """
        执行采集并返回 pipeline-ready 的 fetch_result

        Returns:
            {"events": [...], "metrics": {...}}
        """
        target = SCRAPER_TARGETS.get(competitor_id)
        if not target:
            return {"events": [], "metrics": {}, "error": f"未知竞品: {competitor_id}"}

        # 1. 尝试在线抓取
        raw_data = None
        if not self._use_fixtures:
            raw_data = self._scrape_online(target)

        # 2. 在线失败 → 离线 fixture
        if raw_data is None:
            raw_data = self._load_fixture(competitor_id)
            if raw_data:
                logger.info(f"[Scraper] 竞品{competitor_id} 使用离线fixture")
            else:
                raw_data = self._scrape_fallback(target)

        # 3. 在线成功 → 保存 fixture
        if raw_data and raw_data.get("_source") != "fixture":
            self._save_fixture(competitor_id, raw_data)

        # 4. 结构化 events
        events = self._build_events(competitor_id, raw_data or {}, target)
        metrics = self._extract_metrics(raw_data or {})

        return {"events": events, "metrics": metrics}

    def _scrape_online(self, target: Dict) -> Optional[Dict]:
        """在线抓取 — Playwright 优先, httpx 兜底"""
        # 尝试 Playwright
        try:
            result = self._scrape_with_playwright(target)
            if result and self._is_valid_result(result):
                result["_source"] = "playwright"
                result["_timestamp"] = datetime.utcnow().isoformat()
                logger.info(f"[Scraper] Playwright抓取成功: {target['name']}")
                return result
        except Exception as e:
            logger.warning(f"[Scraper] Playwright抓取失败 ({target['name']}): {e}")

        # 降级为 httpx
        try:
            result = self._scrape_with_httpx(target)
            if result:
                result["_source"] = "httpx"
                result["_timestamp"] = datetime.utcnow().isoformat()
                logger.info(f"[Scraper] httpx抓取成功: {target['name']}")
                return result
        except Exception as e:
            logger.warning(f"[Scraper] httpx抓取失败 ({target['name']}): {e}")

        return None

    def _scrape_with_playwright(self, target: Dict) -> Optional[Dict]:
        """Playwright 无头浏览器抓取"""
        from playwright.sync_api import sync_playwright

        all_products = []
        all_features = []
        all_prices = []

        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                viewport={"width": 1920, "height": 1080},
                locale="zh-CN",
            )
            page = context.new_page()

            for url in target["urls"]:
                try:
                    page.goto(url, wait_until="domcontentloaded", timeout=20000)
                    time.sleep(2)  # 等动态内容渲染

                    content = page.content()

                    # 提取产品名
                    products = page.evaluate("""() => {
                        const results = [];
                        document.querySelectorAll('h1, h2, h3, h4, [class*="title"], [class*="name"], [class*="product"]').forEach(el => {
                            const text = el.textContent.trim();
                            if (text.length > 2 && text.length < 200 && !results.includes(text))
                                results.push(text);
                        });
                        return results.slice(0, 50);
                    }""")
                    all_products.extend(products)

                    # 提取价格
                    prices = page.evaluate("""() => {
                        const results = [];
                        document.querySelectorAll('[class*="price"], [class*="Price"], [class*="cost"], [class*="fee"], .money, [class*="amount"]').forEach(el => {
                            const text = el.textContent.trim();
                            if (text && text.length < 100 && /\\d/.test(text))
                                results.push(text);
                        });
                        return results.slice(0, 30);
                    }""")
                    all_prices.extend(prices)

                    # 提取功能标签
                    features = page.evaluate("""() => {
                        const results = [];
                        document.querySelectorAll('[class*="feature"], [class*="tag"], [class*="label"], [class*="badge"], [class*="capability"]').forEach(el => {
                            const text = el.textContent.trim();
                            if (text.length > 1 && text.length < 100 && !results.includes(text))
                                results.push(text);
                        });
                        return results.slice(0, 50);
                    }""")
                    all_features.extend(features)

                except Exception as e:
                    logger.warning(f"[Scraper] 抓取URL失败 {url}: {e}")
                    continue

            browser.close()

        return {
            "products": list(set(all_products)),
            "prices": list(set(all_prices)),
            "features": list(set(all_features)),
            "page_count": len(target["urls"]),
        }

    def _scrape_with_httpx(self, target: Dict) -> Optional[Dict]:
        """httpx + BeautifulSoup 轻量抓取（无需浏览器）"""
        import httpx
        from bs4 import BeautifulSoup

        all_text = []
        all_links = []

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
            "Accept-Language": "zh-CN,zh;q=0.9",
        }

        with httpx.Client(timeout=15, follow_redirects=True, headers=headers) as client:
            for url in target["urls"]:
                try:
                    resp = client.get(url)
                    resp.raise_for_status()
                    soup = BeautifulSoup(resp.text, "html.parser")

                    # 提取可见文本
                    for tag in soup.find_all(["h1", "h2", "h3", "h4", "p", "span", "a"]):
                        text = tag.get_text(strip=True)
                        if 3 < len(text) < 300:
                            all_text.append(text)
                        href = tag.get("href", "")
                        if href and href.startswith(("http", "/")):
                            all_links.append(href)

                except Exception as e:
                    logger.warning(f"[Scraper] httpx抓取失败 {url}: {e}")
                    continue

        # 从文本中提取产品名和价格
        products = [t for t in all_text if self._looks_like_product(t)]
        prices = [t for t in all_text if self._looks_like_price(t)]
        features = [t for t in all_text if self._looks_like_feature(t)]

        return {
            "products": list(set(products))[:50],
            "prices": list(set(prices))[:30],
            "features": list(set(features))[:50],
            "raw_links": list(set(all_links))[:20],
            "page_count": len(target["urls"]),
        }

    def _scrape_fallback(self, target: Dict) -> Dict:
        """完全离线 — 基于竞品名称和已知信息构造基础数据"""
        name = target["name"]
        return {
            "_source": "fallback",
            "_timestamp": datetime.utcnow().isoformat(),
            "products": [f"{name} 云服务器", f"{name} 对象存储", f"{name} CDN", f"{name} 数据库", f"{name} AI平台"],
            "prices": ["按量付费", "包年包月", "竞价实例"],
            "features": ["弹性伸缩", "安全组", "监控告警", "日志服务", "负载均衡"],
            "page_count": 0,
        }

    # ── 文本识别辅助 ──────────────────────────────────────────

    def _looks_like_product(self, text: str) -> bool:
        """判断文本是否像产品名"""
        keywords = ["云", "服务", "计算", "存储", "数据库", "网络", "安全", "AI", "CDN",
                    "ECS", "RDS", "OSS", "CVM", "COS", "OBS", "EC2", "S3", "BCC",
                    "集群", "引擎", "节点", "实例", "Serverless", "容器", "函数"]
        return any(kw in text for kw in keywords) and len(text) < 100

    def _looks_like_price(self, text: str) -> bool:
        """判断文本是否像价格"""
        price_indicators = ["¥", "元", "/月", "/小时", "/年", "/GB", "/TB", "起",
                           "CNY", "免费", "按量", "包年", "包月", "0.", "1."]
        has_currency = any(ind in text for ind in price_indicators)
        has_digit = bool(re.search(r"\d", text))
        return has_currency and has_digit and len(text) < 80

    def _looks_like_feature(self, text: str) -> bool:
        """判断文本是否像功能特性"""
        feature_kw = ["弹性", "自动", "高可用", "分布式", "智能", "安全", "监控",
                     "备份", "恢复", "迁移", "加速", "优化", "防护", "管理", "控制台",
                     "API", "SDK", "兼容", "多区域", "跨地域", "容器化"]
        return any(kw in text for kw in feature_kw) and len(text) < 60

    def _is_valid_result(self, result: Dict) -> bool:
        """验证抓取结果是否有效"""
        return (len(result.get("products", [])) > 0 or
                len(result.get("prices", [])) > 0 or
                len(result.get("features", [])) > 0)

    # ── Event 构造 ────────────────────────────────────────────

    def _build_events(self, competitor_id: int, raw: Dict, target: Dict) -> List[Dict]:
        """将原始抓取数据转换为 pipeline events"""
        events = []
        now = datetime.utcnow().isoformat()
        source = raw.get("_source", "unknown")
        base_url = target["urls"][0] if target["urls"] else ""

        # 产品发现事件
        for product in raw.get("products", [])[:10]:
            events.append({
                "type": "product_detected",
                "title": product[:100],
                "data": {"product": product, "competitor": target["name"]},
                "source": base_url,
                "timestamp": now,
            })

        # 价格检测事件
        for price_text in raw.get("prices", [])[:8]:
            events.append({
                "type": "price_detected",
                "title": f"价格: {price_text[:80]}",
                "data": {"price_text": price_text, "competitor": target["name"]},
                "source": base_url,
                "timestamp": now,
            })

        # 功能检测事件
        for feature in raw.get("features", [])[:8]:
            events.append({
                "type": "feature_detected",
                "title": f"功能: {feature[:80]}",
                "data": {"feature": feature, "competitor": target["name"]},
                "source": base_url,
                "timestamp": now,
            })

        # 元事件: 记录抓取来源
        events.append({
            "type": "scrape_meta",
            "title": f"数据来源: {source}",
            "data": {"source": source, "page_count": raw.get("page_count", 0), "timestamp": now},
            "source": base_url,
            "timestamp": now,
        })

        return events

    def _extract_metrics(self, raw: Dict) -> Dict:
        """从抓取数据中提取竞品指标"""
        product_count = len(raw.get("products", []))
        feature_count = len(raw.get("features", []))

        metrics = {}
        if product_count > 0:
            metrics["feature_count"] = min(product_count * 3, 250)
        if feature_count > 0:
            metrics["innovation_velocity"] = min(feature_count * 2, 100)

        return metrics

    # ── Fixture 管理 ──────────────────────────────────────────

    def _fixture_path(self, competitor_id: int) -> Path:
        return FIXTURES_DIR / f"{competitor_id}.json"

    def _save_fixture(self, competitor_id: int, raw_data: Dict):
        """保存抓取结果为 fixture"""
        try:
            # 只保存核心数据，去掉内部标记
            save_data = {k: v for k, v in raw_data.items() if not k.startswith("_")}
            save_data["_saved_at"] = datetime.utcnow().isoformat()
            path = self._fixture_path(competitor_id)
            path.write_text(json.dumps(save_data, ensure_ascii=False, indent=2), encoding="utf-8")
            logger.info(f"[Scraper] Fixture已保存: {path}")
        except Exception as e:
            logger.warning(f"[Scraper] 保存fixture失败: {e}")

    def _load_fixture(self, competitor_id: int) -> Optional[Dict]:
        """加载离线 fixture"""
        path = self._fixture_path(competitor_id)
        if not path.exists():
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            data["_source"] = "fixture"
            data["_timestamp"] = data.get("_saved_at", "")
            return data
        except Exception as e:
            logger.warning(f"[Scraper] 加载fixture失败: {e}")
            return None


scraper_engine = ScraperEngine()
