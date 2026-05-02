"""
采集服务 - 参考changedetection.io/Price-Tracking-Web-Scraper/price-tracker-bot
集成Playwright反检测 + CSS选择器提取 + 价格解析 + 采集调度  SQLAlchemy ORM
"""
import asyncio
import hashlib
import json
import time
import logging
from datetime import datetime
from typing import Optional, Dict, Any, List
from contextlib import contextmanager

from sqlalchemy.orm import Session

from app.core.models import ScraperConfig, ScrapeResult

logger = logging.getLogger(__name__)


class ScraperService:
    """采集服务"""

    def __init__(self, db: Session = None):
        self._injected_db = db
        self._browser = None
        self._playwright = None

    @contextmanager
    def _session(self):
        if self._injected_db:
            yield self._injected_db
        else:
            from app.core.database import SessionLocal
            session = SessionLocal()
            try:
                yield session
                session.commit()
            except Exception:
                session.rollback()
                raise
            finally:
                session.close()

    def _config_to_dict(self, cfg: ScraperConfig) -> Dict:
        """Convert ScraperConfig ORM object to dict matching legacy format."""
        return {
            "id": cfg.id,
            "competitor_id": cfg.competitor_id,
            "name": cfg.name,
            "target_url": cfg.target_url,
            "scrape_type": cfg.scrape_type,
            "selectors": cfg.selectors,
            "headers": cfg.headers,
            "wait_selector": cfg.wait_selector,
            "wait_timeout": cfg.wait_timeout,
            "use_stealth": cfg.use_stealth,
            "frequency_minutes": cfg.frequency_minutes,
            "enabled": cfg.enabled,
            "last_run_at": cfg.last_run_at,
            "last_status": cfg.last_status,
            "last_error": cfg.last_error,
            "created_at": cfg.created_at,
            "updated_at": cfg.updated_at,
        }

    def _result_to_dict(self, sr: ScrapeResult) -> Dict:
        """Convert ScrapeResult ORM object to dict matching legacy format."""
        return {
            "id": sr.id,
            "config_id": sr.config_id,
            "competitor_id": sr.competitor_id,
            "extracted_data": sr.extracted_data,
            "price": sr.price,
            "title": sr.title,
            "in_stock": sr.in_stock,
            "checksum": sr.checksum,
            "scrape_duration_ms": sr.scrape_duration_ms,
            "status": sr.status,
            "error_message": sr.error_message,
            "created_at": sr.created_at,
        }

    # ========== 采集规则配置 ==========

    def create_config(self, competitor_id: int, name: str, target_url: str,
                      scrape_type: str = 'playwright', selectors: dict = None,
                      headers: dict = None, wait_selector: str = None,
                      wait_timeout: int = 10000, use_stealth: bool = True,
                      frequency_minutes: int = 60) -> int:
        """创建采集规则"""
        with self._session() as db:
            cfg = ScraperConfig(
                competitor_id=competitor_id,
                name=name,
                target_url=target_url,
                scrape_type=scrape_type,
                selectors=selectors,
                headers=headers,
                wait_selector=wait_selector,
                wait_timeout=wait_timeout,
                use_stealth=use_stealth,
                frequency_minutes=frequency_minutes,
                enabled=True,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
            db.add(cfg)
            db.flush()
            db.refresh(cfg)
            return cfg.id

    def update_config(self, config_id: int, **kwargs) -> bool:
        """更新采集规则"""
        allowed = {'name', 'target_url', 'scrape_type', 'selectors', 'headers',
                   'wait_selector', 'wait_timeout', 'use_stealth', 'frequency_minutes', 'enabled'}
        updates = {k: v for k, v in kwargs.items() if k in allowed}

        if not updates:
            return False

        # JSON-serializable fields are passed as dicts already, no need to re-serialize
        updates['updated_at'] = datetime.utcnow()

        with self._session() as db:
            result = (
                db.query(ScraperConfig)
                .filter(ScraperConfig.id == config_id)
                .update(updates, synchronize_session=False)
            )
            return result > 0

    def get_configs(self, competitor_id: int = None, enabled_only: bool = False) -> List[Dict]:
        """获取采集规则列表"""
        with self._session() as db:
            q = db.query(ScraperConfig)
            if competitor_id:
                q = q.filter(ScraperConfig.competitor_id == competitor_id)
            if enabled_only:
                q = q.filter(ScraperConfig.enabled == True)
            q = q.order_by(ScraperConfig.id.desc())
            configs = q.all()
            return [self._config_to_dict(c) for c in configs]

    def get_config(self, config_id: int) -> Optional[Dict]:
        """获取单个采集规则"""
        with self._session() as db:
            cfg = db.query(ScraperConfig).filter(ScraperConfig.id == config_id).first()
            return self._config_to_dict(cfg) if cfg else None

    def delete_config(self, config_id: int) -> bool:
        """删除采集规则"""
        with self._session() as db:
            db.query(ScraperConfig).filter(ScraperConfig.id == config_id).delete()
            return True

    # ========== 采集执行 ==========

    async def fetch_and_extract(self, config_id: int) -> Dict[str, Any]:
        """根据配置执行采集+提取"""
        config = self.get_config(config_id)
        if not config:
            return {'success': False, 'error': '配置不存在'}

        start_time = time.time()
        result = {
            'config_id': config_id,
            'competitor_id': config['competitor_id'],
            'status': 'success',
            'extracted_data': {},
            'price': None,
            'title': None,
            'in_stock': None,
            'error_message': None
        }

        try:
            if config['scrape_type'] == 'playwright':
                extracted = await self._fetch_with_playwright(config)
            elif config['scrape_type'] == 'requests':
                extracted = await self._fetch_with_requests(config)
            else:
                extracted = await self._fetch_with_playwright(config)

            result['extracted_data'] = extracted
            result['price'] = self._parse_price(extracted.get('price'))
            result['title'] = extracted.get('title')
            result['in_stock'] = extracted.get('in_stock')
            result['checksum'] = self._calculate_checksum(extracted)

            # 更新配置状态
            with self._session() as db:
                db.query(ScraperConfig).filter(ScraperConfig.id == config_id).update({
                    ScraperConfig.last_run_at: datetime.utcnow(),
                    ScraperConfig.last_status: 'success',
                    ScraperConfig.last_error: None,
                }, synchronize_session=False)

        except Exception as e:
            result['status'] = 'error'
            result['error_message'] = str(e)
            logger.error(f"采集失败 config={config_id}: {e}")

            with self._session() as db:
                db.query(ScraperConfig).filter(ScraperConfig.id == config_id).update({
                    ScraperConfig.last_run_at: datetime.utcnow(),
                    ScraperConfig.last_status: 'error',
                    ScraperConfig.last_error: str(e)[:200],
                }, synchronize_session=False)

        result['scrape_duration_ms'] = int((time.time() - start_time) * 1000)

        # 保存结果
        self._save_result(result)

        return result

    async def _fetch_with_playwright(self, config: Dict) -> Dict[str, str]:
        """使用Playwright采集（参考changedetection.io + Camoufox反检测）"""
        from playwright.async_api import async_playwright

        selectors = config.get('selectors') or {}
        if isinstance(selectors, str):
            selectors = json.loads(selectors)
        extracted = {}

        pw = await async_playwright().start()
        try:
            launch_args = []
            if config.get('use_stealth'):
                # 反检测参数（参考Camoufox）
                launch_args = [
                    '--disable-blink-features=AutomationControlled',
                    '--disable-features=IsolateOrigins,site-per-process',
                    '--disable-infobars',
                    '--no-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-gpu',
                ]

            browser = await pw.chromium.launch(
                headless=True,
                args=launch_args
            )

            context = await browser.new_context(
                user_agent=self._get_user_agent(),
                viewport={'width': 1920, 'height': 1080},
                locale='zh-CN',
                timezone_id='Asia/Shanghai',
                java_script_enabled=True,
            )

            # 反检测：注入stealth脚本
            if config.get('use_stealth'):
                await context.add_init_script("""
                    Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                    Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
                    Object.defineProperty(navigator, 'languages', {get: () => ['zh-CN', 'zh', 'en']});
                    window.chrome = {runtime: {}};
                """)

            page = await context.new_page()

            # 设置自定义headers
            custom_headers = config.get('headers') or {}
            if isinstance(custom_headers, str):
                custom_headers = json.loads(custom_headers)
            if custom_headers:
                await page.set_extra_http_headers(custom_headers)

            # 导航到目标页面
            wait_selector = config.get('wait_selector')
            wait_timeout = config.get('wait_timeout', 10000)

            await page.goto(config['target_url'], wait_until='domcontentloaded', timeout=wait_timeout)

            # 等待关键元素
            if wait_selector:
                try:
                    await page.wait_for_selector(wait_selector, timeout=wait_timeout)
                except Exception:
                    logger.warning(f"等待元素超时: {wait_selector}")

            # 额外等待动态内容加载
            await page.wait_for_timeout(1000)

            # 根据选择器提取数据
            for field_name, selector in selectors.items():
                try:
                    if selector.startswith('attr:'):
                        # 属性提取: attr:href => a.link
                        attr_name, css_sel = selector[5:].split(':', 1)
                        el = await page.query_selector(css_sel)
                        if el:
                            extracted[field_name] = await el.get_attribute(attr_name) or ''
                    elif selector.startswith('text:'):
                        # 文本提取（多个元素拼接）
                        css_sel = selector[5:]
                        elements = await page.query_selector_all(css_sel)
                        texts = []
                        for el in elements[:10]:
                            t = await el.text_content()
                            if t:
                                texts.append(t.strip())
                        extracted[field_name] = ' | '.join(texts)
                    else:
                        # 默认文本提取
                        el = await page.query_selector(selector)
                        if el:
                            extracted[field_name] = (await el.text_content() or '').strip()
                except Exception as e:
                    logger.warning(f"提取字段 {field_name} 失败: {e}")
                    extracted[field_name] = ''

            # 如果没有配置选择器，尝试智能提取
            if not selectors:
                extracted = await self._smart_extract(page)

            await browser.close()

        except Exception as e:
            logger.error(f"Playwright采集异常: {e}")
            raise
        finally:
            await pw.stop()

        return extracted

    async def _fetch_with_requests(self, config: Dict) -> Dict[str, str]:
        """使用requests采集（轻量模式，适合静态页面）"""
        import httpx
        from bs4 import BeautifulSoup

        selectors = config.get('selectors') or {}
        if isinstance(selectors, str):
            selectors = json.loads(selectors)
        extracted = {}

        headers = {
            'User-Agent': self._get_user_agent(),
            'Accept': 'text/html,application/xhtml+xml',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        }
        custom_headers = config.get('headers') or {}
        if isinstance(custom_headers, str):
            custom_headers = json.loads(custom_headers)
        headers.update(custom_headers)

        async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
            resp = await client.get(config['target_url'], headers=headers)
            resp.raise_for_status()

        soup = BeautifulSoup(resp.text, 'html.parser')

        for field_name, selector in selectors.items():
            try:
                if selector.startswith('attr:'):
                    attr_name, css_sel = selector[5:].split(':', 1)
                    el = soup.select_one(css_sel)
                    extracted[field_name] = el.get(attr_name, '') if el else ''
                else:
                    el = soup.select_one(selector)
                    extracted[field_name] = el.get_text(strip=True) if el else ''
            except Exception as e:
                logger.warning(f"提取字段 {field_name} 失败: {e}")
                extracted[field_name] = ''

        # 智能提取兜底
        if not selectors:
            extracted = self._smart_extract_static(soup)

        return extracted

    async def _smart_extract(self, page) -> Dict[str, str]:
        """智能提取（无选择器时自动识别价格/标题/库存）"""
        extracted = {}

        # 常见价格选择器模式
        price_patterns = [
            '.price', '.product-price', '.sale-price', '.current-price',
            '[data-price]', '.price-current', '.p-price', '.price-text',
            '.product-price-current', '.item-price', '.price-box .price',
        ]
        for sel in price_patterns:
            el = await page.query_selector(sel)
            if el:
                text = (await el.text_content() or '').strip()
                if text and any(c.isdigit() for c in text):
                    extracted['price'] = text
                    break

        # 常见标题选择器
        title_patterns = ['h1', '.product-title', '.product-name', '[data-title]', '.item-title']
        for sel in title_patterns:
            el = await page.query_selector(sel)
            if el:
                text = (await el.text_content() or '').strip()
                if text and len(text) > 2:
                    extracted['title'] = text
                    break

        # 库存状态
        stock_patterns = [
            ('.stock', '有货'),
            ('.out-of-stock', '缺货'),
            ('.add-to-cart', '可购买'),
            ('button.buy', '可购买'),
        ]
        for sel, status in stock_patterns:
            el = await page.query_selector(sel)
            if el:
                is_visible = await el.is_visible()
                if is_visible:
                    extracted['in_stock'] = 'true' if status in ('有货', '可购买') else 'false'
                    break

        return extracted

    def _smart_extract_static(self, soup) -> Dict[str, str]:
        """静态页面智能提取"""
        from bs4 import BeautifulSoup
        extracted = {}

        price_patterns = ['.price', '.product-price', '.sale-price', '[data-price]', '.p-price']
        for sel in price_patterns:
            el = soup.select_one(sel)
            if el:
                text = el.get_text(strip=True)
                if text and any(c.isdigit() for c in text):
                    extracted['price'] = text
                    break

        title_patterns = ['h1', '.product-title', '.product-name']
        for sel in title_patterns:
            el = soup.select_one(sel)
            if el:
                text = el.get_text(strip=True)
                if text and len(text) > 2:
                    extracted['title'] = text
                    break

        return extracted

    # ========== 价格解析 ==========

    def _parse_price(self, price_str: str) -> Optional[float]:
        """解析价格字符串为浮点数（参考price-parser）"""
        if not price_str:
            return None

        import re
        # 移除货币符号和空格
        cleaned = re.sub(r'[¥￥$€£₹]', '', price_str)
        cleaned = re.sub(r'[^\d.,]', '', cleaned)

        if not cleaned:
            return None

        # 处理中文数字格式: 1,234.56 或 1.234,56
        if ',' in cleaned and '.' in cleaned:
            if cleaned.rfind(',') > cleaned.rfind('.'):
                # 欧洲格式: 1.234,56
                cleaned = cleaned.replace('.', '').replace(',', '.')
            else:
                # 标准格式: 1,234.56
                cleaned = cleaned.replace(',', '')
        elif ',' in cleaned:
            # 判断逗号是千分位还是小数点
            parts = cleaned.split(',')
            if len(parts[-1]) == 2:
                cleaned = cleaned.replace(',', '.')
            else:
                cleaned = cleaned.replace(',', '')

        try:
            return float(cleaned)
        except ValueError:
            return None

    # ========== 工具方法 ==========

    def _calculate_checksum(self, data: Dict) -> str:
        """计算内容校验和"""
        content = json.dumps(data, sort_keys=True, ensure_ascii=False)
        return hashlib.md5(content.encode()).hexdigest()

    def _get_user_agent(self) -> str:
        """随机User-Agent"""
        agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:126.0) Gecko/20100101 Firefox/126.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Safari/605.1.15',
        ]
        import random
        return random.choice(agents)

    def _save_result(self, result: Dict):
        """保存采集结果"""
        with self._session() as db:
            sr = ScrapeResult(
                config_id=result['config_id'],
                competitor_id=result['competitor_id'],
                extracted_data=result.get('extracted_data', {}),
                price=result.get('price'),
                title=result.get('title'),
                in_stock=True if result.get('in_stock') == 'true' else (False if result.get('in_stock') == 'false' else None),
                checksum=result.get('checksum'),
                scrape_duration_ms=result.get('scrape_duration_ms'),
                status=result.get('status', 'success'),
                error_message=result.get('error_message'),
                created_at=datetime.utcnow(),
            )
            db.add(sr)

    # ========== 采集历史 ==========

    def get_results(self, competitor_id: int = None, config_id: int = None,
                    limit: int = 20) -> List[Dict]:
        """获取采集结果历史"""
        with self._session() as db:
            q = db.query(ScrapeResult)
            if competitor_id:
                q = q.filter(ScrapeResult.competitor_id == competitor_id)
            if config_id:
                q = q.filter(ScrapeResult.config_id == config_id)
            q = q.order_by(ScrapeResult.created_at.desc()).limit(limit)
            results = q.all()
            return [self._result_to_dict(r) for r in results]

    def get_latest_result(self, competitor_id: int) -> Optional[Dict]:
        """获取竞品最新采集结果"""
        with self._session() as db:
            sr = (
                db.query(ScrapeResult)
                .filter(ScrapeResult.competitor_id == competitor_id)
                .order_by(ScrapeResult.created_at.desc())
                .first()
            )
            return self._result_to_dict(sr) if sr else None

    # ========== 批量采集 ==========

    async def run_all_enabled(self) -> List[Dict]:
        """执行所有启用的采集任务"""
        configs = self.get_configs(enabled_only=True)
        results = []

        for config in configs:
            try:
                result = await self.fetch_and_extract(config['id'])
                results.append(result)
                logger.info(f"采集完成: config={config['id']} competitor={config['competitor_id']} status={result['status']}")
            except Exception as e:
                logger.error(f"采集异常: config={config['id']} error={e}")
                results.append({
                    'config_id': config['id'],
                    'competitor_id': config['competitor_id'],
                    'status': 'error',
                    'error_message': str(e)
                })

        return results


scraper_service = ScraperService()
