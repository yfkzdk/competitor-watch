"""
Playwright浏览器自动化服务
"""
from playwright.async_api import async_playwright, Browser, Page
from typing import Dict, Optional, List
import asyncio
from datetime import datetime
import json

class PlaywrightService:
    """Playwright浏览器自动化服务"""

    def __init__(self):
        self.browser: Optional[Browser] = None
        self.playwright = None

    async def initialize(self):
        """初始化Playwright"""
        if not self.playwright:
            self.playwright = await async_playwright().start()
            self.browser = await self.playwright.chromium.launch(headless=True)
            print("[Playwright] 浏览器已启动")

    async def shutdown(self):
        """关闭Playwright"""
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
        print("[Playwright] 浏览器已关闭")

    async def fetch_page_content(self, url: str, wait_time: int = 3000) -> Dict:
        """获取页面内容"""
        if not self.browser:
            await self.initialize()

        page = None
        try:
            page = await self.browser.new_page()

            # 访问页面
            await page.goto(url, wait_until='networkidle')

            # 等待页面加载
            await page.wait_for_timeout(wait_time)

            # 获取页面内容
            content = await page.content()
            title = await page.title()

            # 获取页面文本
            text_content = await page.evaluate('() => document.body.innerText')

            return {
                'success': True,
                'url': url,
                'title': title,
                'html': content,
                'text': text_content,
                'timestamp': datetime.now().isoformat()
            }

        except Exception as e:
            return {
                'success': False,
                'url': url,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
        finally:
            if page:
                await page.close()

    async def fetch_price_info(self, url: str, selectors: Dict[str, str]) -> Dict:
        """获取价格信息"""
        if not self.browser:
            await self.initialize()

        page = None
        try:
            page = await self.browser.new_page()
            await page.goto(url, wait_until='networkidle')
            await page.wait_for_timeout(2000)

            result = {'url': url, 'timestamp': datetime.now().isoformat()}

            # 提取价格
            if 'price' in selectors:
                price_element = await page.query_selector(selectors['price'])
                if price_element:
                    price_text = await price_element.inner_text()
                    result['price'] = self._parse_price(price_text)

            # 提取标题
            if 'title' in selectors:
                title_element = await page.query_selector(selectors['title'])
                if title_element:
                    result['title'] = await title_element.inner_text()

            # 提取库存状态
            if 'stock' in selectors:
                stock_element = await page.query_selector(selectors['stock'])
                if stock_element:
                    stock_text = await stock_element.inner_text()
                    result['in_stock'] = '有货' in stock_text or 'in stock' in stock_text.lower()

            result['success'] = True
            return result

        except Exception as e:
            return {
                'success': False,
                'url': url,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
        finally:
            if page:
                await page.close()

    async def take_screenshot(self, url: str, full_page: bool = True) -> Dict:
        """截取页面截图"""
        if not self.browser:
            await self.initialize()

        page = None
        try:
            page = await self.browser.new_page()
            await page.goto(url, wait_until='networkidle')
            await page.wait_for_timeout(2000)

            screenshot_bytes = await page.screenshot(full_page=full_page)

            return {
                'success': True,
                'url': url,
                'screenshot': screenshot_bytes,
                'timestamp': datetime.now().isoformat()
            }

        except Exception as e:
            return {
                'success': False,
                'url': url,
                'error': str(e)
            }
        finally:
            if page:
                await page.close()

    async def execute_browser_steps(self, url: str, steps: List[Dict]) -> Dict:
        """执行浏览器交互步骤"""
        if not self.browser:
            await self.initialize()

        page = None
        try:
            page = await self.browser.new_page()
            await page.goto(url, wait_until='networkidle')

            # 执行步骤
            for step in steps:
                step_type = step.get('type')

                if step_type == 'click':
                    selector = step.get('selector')
                    await page.click(selector)

                elif step_type == 'fill':
                    selector = step.get('selector')
                    value = step.get('value')
                    await page.fill(selector, value)

                elif step_type == 'wait':
                    timeout = step.get('timeout', 1000)
                    await page.wait_for_timeout(timeout)

                elif step_type == 'scroll':
                    selector = step.get('selector')
                    if selector:
                        await page.locator(selector).scroll_into_view_if_needed()

            # 获取最终内容
            content = await page.content()
            text = await page.evaluate('() => document.body.innerText')

            return {
                'success': True,
                'url': url,
                'html': content,
                'text': text,
                'timestamp': datetime.now().isoformat()
            }

        except Exception as e:
            return {
                'success': False,
                'url': url,
                'error': str(e)
            }
        finally:
            if page:
                await page.close()

    def _parse_price(self, price_text: str) -> Optional[float]:
        """解析价格文本"""
        import re
        # 移除货币符号和空格
        cleaned = re.sub(r'[^\d.,]', '', price_text)
        # 替换逗号为点
        cleaned = cleaned.replace(',', '.')
        try:
            return float(cleaned)
        except (ValueError, TypeError):
            return None

# 全局服务实例
playwright_service = PlaywrightService()
