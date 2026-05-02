"""
通知服务 — 基于 Apprise 的多通道通知
支持 80+ 通道: 邮件、Slack、钉钉、企业微信、Telegram、Webhook 等
"""
import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class NotificationService:
    """多通道通知服务"""

    def __init__(self):
        self._apprise = None
        self._channels: Dict[str, dict] = {}
        self._load_config()

    def _load_config(self):
        """从配置加载通知通道"""
        try:
            import json
            from pathlib import Path
            config_path = Path(__file__).parent.parent.parent / "config" / "notifications.json"
            if config_path.exists():
                with open(config_path, encoding="utf-8") as f:
                    cfg = json.load(f)
                for ch in cfg.get("channels", []):
                    self._channels[ch["name"]] = ch
        except Exception as e:
            logger.debug(f"通知配置加载失败: {e}")

    @property
    def apprise(self):
        """懒加载 Apprise"""
        if self._apprise is None:
            try:
                import apprise
                self._apprise = apprise.Apprise()
                # 注册已配置的通道
                for name, ch in self._channels.items():
                    url = ch.get("url", "")
                    if url:
                        self._apprise.add(url, tag=name)
                logger.info(f"[Notification] Apprise 初始化, {len(self._channels)} 通道")
            except ImportError:
                logger.warning("[Notification] apprise 未安装, pip install apprise")
                self._apprise = False
        return self._apprise if self._apprise is not False else None

    def list_channels(self) -> List[dict]:
        """列出已配置的通知通道"""
        result = []
        for name, ch in self._channels.items():
            result.append({
                "name": name,
                "type": ch.get("type", "unknown"),
                "enabled": ch.get("enabled", True),
                "url_set": bool(ch.get("url")),
            })
        return result

    def test_channel(self, channel_name: str) -> Dict:
        """测试通知通道连通性"""
        ch = self._channels.get(channel_name)
        if not ch:
            return {"success": False, "error": f"通道 {channel_name} 不存在"}

        url = ch.get("url", "")
        if not url:
            return {"success": False, "error": f"通道 {channel_name} 未配置 URL"}

        if not self.apprise:
            return {"success": False, "error": "Apprise 未安装"}

        try:
            import apprise
            a = apprise.Apprise()
            a.add(url)
            ok = a.notify(
                title="[竞品监控] 通道测试",
                body=f"通道 {channel_name} 连通性测试成功",
            )
            return {"success": ok, "channel": channel_name}
        except Exception as e:
            return {"success": False, "error": str(e)[:200]}

    def send(
        self,
        title: str,
        body: str = "",
        channels: Optional[List[str]] = None,
        severity: str = "info",
    ) -> Dict:
        """
        发送通知

        Args:
            title: 通知标题
            body: 通知正文
            channels: 指定通道列表（None=全部）
            severity: 严重级别 (info/warning/critical)
        """
        if not self.apprise:
            logger.warning(f"[Notification] Apprise 不可用, 跳过通知: {title}")
            return {"sent": False, "reason": "apprise_unavailable"}

        # 格式化消息
        severity_emoji = {"info": "", "warning": "⚠️ ", "critical": "🚨 "}
        formatted_title = f"{severity_emoji.get(severity, '')}{title}"
        formatted_body = body or title

        sent_count = 0
        failed = []

        if channels:
            # 指定通道
            for ch_name in channels:
                if ch_name in self._channels:
                    try:
                        ok = self.apprise.notify(
                            title=formatted_title,
                            body=formatted_body,
                            tag=ch_name,
                        )
                        if ok:
                            sent_count += 1
                        else:
                            failed.append(ch_name)
                    except Exception as e:
                        failed.append(f"{ch_name}: {e}")
        else:
            # 全部通道
            try:
                ok = self.apprise.notify(
                    title=formatted_title,
                    body=formatted_body,
                )
                if ok:
                    sent_count = len(self._channels)
                else:
                    failed = list(self._channels.keys())
            except Exception as e:
                failed.append(str(e))

        return {
            "sent": sent_count > 0,
            "sent_count": sent_count,
            "failed": failed,
        }

    def add_channel(self, name: str, channel_type: str, url: str, enabled: bool = True):
        """动态添加通知通道"""
        self._channels[name] = {
            "name": name,
            "type": channel_type,
            "url": url,
            "enabled": enabled,
        }
        if self.apprise and enabled:
            self.apprise.add(url, tag=name)

    def remove_channel(self, name: str):
        """移除通知通道"""
        if name in self._channels:
            del self._channels[name]
            # Apprise 不支持移除单个通道，需要重建
            self._apprise = None


notification_service = NotificationService()
