"""
模拟实时监控 — 后台线程基于种子数据生成合理波动

场景:
  - 每 20~35 秒随机选择一个竞品
  - 50% 概率: 取最新价格做 ±2% 波动
  - 30% 概率: 生成逼真用户评论
  - 20% 概率: 生成变更记录 (触发 pipeline 检测 → 告警)

Demo 使用时启动: 数据会自己在流动，WebSocket 自动推送
"""
import logging
import random
import threading
import time
from datetime import datetime
from contextlib import contextmanager

from sqlalchemy import func

logger = logging.getLogger(__name__)

FEATURES = ["AI分析", "数据导出", "实时监控", "自动扩缩容", "多区域部署",
            "安全审计", "API网关", "日志管理", "权限控制", "容器编排", "Serverless",
            "跨地域复制", "智能降噪", "竞价实例", "冷热分层"]

REAL_PRODUCT_NAMES = {
    1: ["ECS通用型g7", "RDS MySQL高可用版", "OSS标准存储", "CDN流量包", "ACK Pro", "通义千问API"],
    2: ["CVM标准型S5", "云数据库MySQL", "COS标准存储", "CDN流量包", "TDSQL", "TRTC实时音视频"],
    3: ["ECS通用型s6", "GaussDB", "OBS标准存储", "CDN流量包", "ModelArts", "盘古大模型API"],
    4: ["EC2 t3.large", "RDS MySQL", "S3标准存储", "CloudFront", "ElastiCache", "SageMaker"],
    5: ["BCC通用型g5", "RDS MySQL", "BOS标准存储", "CDN流量包", "文心一言API"],
}


class SimulationService:
    def __init__(self, db=None):
        self._injected_db = db
        self._thread = None
        self._running = False
        self._interval = (20, 35)

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

    @property
    def is_running(self):
        return self._running

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._run, daemon=True, name="simulation")
        self._thread.start()
        logger.info("[Simulation] 实时模拟已启动 (interval=20-35s)")

    def stop(self):
        self._running = False
        logger.info("[Simulation] 实时模拟已停止")

    def _run(self):
        while self._running:
            try:
                self._tick()
            except Exception as e:
                logger.error(f"[Simulation] 错误: {e}")
            time.sleep(random.randint(*self._interval))

    def _tick(self):
        from app.core.models import Competitor

        with self._session() as db:
            comps = db.query(Competitor.id, Competitor.name, Competitor.price_index).filter(
                Competitor.status != "deleted"
            ).all()
        if not comps:
            return
        comp = random.choice(comps)
        comp_id, comp_name, price_index = comp.id, comp.name, comp.price_index or 90

        action = random.choices(["price", "review", "change"], weights=[0.5, 0.3, 0.2], k=1)[0]

        if action == "price":
            self._simulate_price(comp_id, comp_name, price_index)
            logger.info(f"[Simulation] {comp_name}: 价格波动")
        elif action == "review":
            self._simulate_review(comp_id, comp_name)
            logger.info(f"[Simulation] {comp_name}: 新评论")
        else:
            self._simulate_change(comp_id, comp_name)
            logger.info(f"[Simulation] {comp_name}: 变更记录")

    def _simulate_price(self, comp_id: int, comp_name: str, price_index: float):
        from app.core.models import PriceHistory

        with self._session() as db:
            last = db.query(PriceHistory).filter(
                PriceHistory.competitor_id == comp_id
            ).order_by(PriceHistory.recorded_at.desc()).first()

            if last and last.price:
                base_price = float(last.price)
                product_name = last.product_name or comp_name
                source = last.source or "simulation"
                orig_price = float(last.original_price) if last.original_price else base_price * 1.05
            else:
                base_price = round(price_index * 3, 2)
                product_name = comp_name
                source = "simulation"
                orig_price = round(base_price * 1.05, 2)

            change_pct = random.uniform(-0.02, 0.02)
            new_price = round(base_price * (1 + change_pct), 2)
            now = datetime.utcnow()

            db.add(PriceHistory(
                competitor_id=comp_id,
                product_name=product_name,
                price=new_price,
                original_price=round(orig_price, 2),
                currency="CNY",
                source=source,
                recorded_at=now,
            ))

    def _simulate_review(self, comp_id: int, comp_name: str):
        """从真实风格评论池中随机抽取一条"""
        from app.core.models import UserReview
        from app.services.review_pool import get_reviews_for_competitor

        # 从评论池随机取一条该竞品的评论
        reviews = get_reviews_for_competitor(comp_id, count=1)
        if not reviews:
            return
        r = reviews[0]

        with self._session() as db:
            db.add(UserReview(
                competitor_id=r["competitor_id"],
                platform=r["platform"],
                author=r["author"],
                rating=r["rating"],
                content=r["content"],
                sentiment_score=r["sentiment_score"],
                review_date=r["review_date"],
                collected_at=r["collected_at"],
            ))

    def _simulate_change(self, comp_id: int, comp_name: str):
        from app.core.models import Change

        change_types = ["price_change", "feature_update", "version_change", "new_product"]
        weights = [0.3, 0.4, 0.2, 0.1]
        change_type = random.choices(change_types, weights=weights, k=1)[0]

        product_names = REAL_PRODUCT_NAMES.get(comp_id, [comp_name])

        if change_type == "price_change":
            product = random.choice(product_names)
            field = f"{product} 价格"
            old_price = round(random.uniform(100, 800), 2)
            new_price = round(old_price * random.uniform(0.85, 0.97), 2)
            old_val = f"{old_price}元/月"
            new_val = f"{new_price}元/月 (降{round((1 - new_price/old_price) * 100)}%)"
            severity = "P1"
        elif change_type == "feature_update":
            feature = random.choice(FEATURES)
            field = f"{random.choice(product_names)}-{feature}"
            old_val = "旧版"
            new_val = f"v{random.randint(1,4)}.{random.randint(0,9)} 已上线"
            severity = "P2"
        elif change_type == "version_change":
            product = random.choice(product_names)
            field = f"{product} 版本"
            minor = random.randint(0, 9)
            old_val = f"v{random.randint(1,3)}.{minor}.{random.randint(0,9)}"
            new_val = f"v{random.randint(2,5)}.{minor + random.randint(1,5)}.{random.randint(0,9)}"
            severity = "P2"
        else:
            product = random.choice(product_names)
            field = f"新产品: {product}"
            old_val = ""
            new_val = "已发布"
            severity = "P0"

        now = datetime.utcnow()
        db = None
        with self._session() as db:
            db.add(Change(
                competitor_id=comp_id,
                field_name=field,
                old_value=old_val,
                new_value=new_val,
                change_type=change_type,
                severity=severity,
                detected_at=now,
                is_read=False,
            ))

        if severity in ("P0", "P1") and random.random() < 0.6:
            self._trigger_alert(comp_id, comp_name, change_type, field, severity)

    def _trigger_alert(self, comp_id: int, comp_name: str, alert_type: str, field: str, severity: str):
        from app.core.models import AlertHistory

        messages = {
            "price_change": f"{comp_name} {field}发生显著变化",
            "feature_update": f"{comp_name} {field}新功能上线",
            "version_change": f"{comp_name} {field}版本更新",
            "new_product": f"{comp_name} {field}新产品发布",
        }
        now = datetime.utcnow()
        with self._session() as db:
            db.add(AlertHistory(
                competitor_id=comp_id,
                message=messages.get(alert_type, f"{comp_name} 检测到变更: {field}"),
                severity=severity,
                is_read=False,
                triggered_at=now,
            ))


simulation = SimulationService()
