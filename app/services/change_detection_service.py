"""
变化检测服务 - 基于changedetection.io核心逻辑  SQLAlchemy ORM
"""
from typing import Dict, Optional, Any
import hashlib
import json
from datetime import datetime
from contextlib import contextmanager

from sqlalchemy.orm import Session

from app.core.models import MonitoringSnapshot


class ChangeDetectionService:
    """变化检测服务"""

    def __init__(self, db: Session = None):
        self._injected_db = db
        self.thresholds = {
            'price_change': 0.05,  # 价格变化5%触发
            'sentiment_change': 0.2,  # 情感变化20%触发
            'stock_change': True,  # 库存变化立即触发
        }

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

    def calculate_checksum(self, content: str) -> str:
        """计算内容校验和"""
        return hashlib.md5(content.encode('utf-8')).hexdigest()

    def detect_price_change(self, old_price: float, new_price: float) -> Optional[Dict]:
        """检测价格变化"""
        if old_price == 0:
            return None

        change_rate = (new_price - old_price) / old_price
        abs_change = abs(change_rate)

        if abs_change > self.thresholds['price_change']:
            severity = self._calculate_severity(abs_change)
            return {
                'type': 'price_change',
                'old_price': old_price,
                'new_price': new_price,
                'change_rate': change_rate,
                'change_percentage': change_rate * 100,
                'severity': severity,
                'timestamp': datetime.now().isoformat()
            }
        return None

    def detect_sentiment_change(self, old_sentiment: Dict, new_sentiment: Dict) -> Optional[Dict]:
        """检测情感变化"""
        old_positive = old_sentiment.get('positive', 0)
        new_positive = new_sentiment.get('positive', 0)

        if old_positive == 0:
            return None

        change_rate = abs(new_positive - old_positive) / old_positive

        if change_rate > self.thresholds['sentiment_change']:
            return {
                'type': 'sentiment_change',
                'old_sentiment': old_sentiment,
                'new_sentiment': new_sentiment,
                'change_rate': change_rate,
                'severity': 'P1' if change_rate > 0.5 else 'P2',
                'timestamp': datetime.now().isoformat()
            }
        return None

    def detect_stock_change(self, old_stock: bool, new_stock: bool) -> Optional[Dict]:
        """检测库存变化"""
        if old_stock != new_stock:
            return {
                'type': 'stock_change',
                'old_stock': old_stock,
                'new_stock': new_stock,
                'severity': 'P0',  # 库存变化优先级最高
                'timestamp': datetime.now().isoformat()
            }
        return None

    def _calculate_severity(self, change_rate: float) -> str:
        """计算告警严重程度"""
        if change_rate > 0.3:  # 30%以上变化
            return 'P0'
        elif change_rate > 0.15:  # 15%以上变化
            return 'P1'
        elif change_rate > 0.05:  # 5%以上变化
            return 'P2'
        else:
            return 'P3'

    def save_snapshot(self, competitor_id: int, snapshot_type: str, data: Dict) -> int:
        """保存快照"""
        snapshot_json = json.dumps(data, ensure_ascii=False)
        hash_value = self.calculate_checksum(snapshot_json)

        with self._session() as db:
            snapshot = MonitoringSnapshot(
                competitor_id=competitor_id,
                snapshot_type=snapshot_type,
                content=snapshot_json,
                content_hash=hash_value,
                captured_at=datetime.utcnow(),
            )
            db.add(snapshot)
            db.flush()
            db.refresh(snapshot)
            return snapshot.id

    def get_last_snapshot(self, competitor_id: int, snapshot_type: str) -> Optional[Dict]:
        """获取最后一次快照"""
        with self._session() as db:
            snapshot = (
                db.query(MonitoringSnapshot)
                .filter(
                    MonitoringSnapshot.competitor_id == competitor_id,
                    MonitoringSnapshot.snapshot_type == snapshot_type,
                )
                .order_by(MonitoringSnapshot.captured_at.desc())
                .first()
            )

        if snapshot and snapshot.content:
            return {
                'data': json.loads(snapshot.content) if isinstance(snapshot.content, str) else snapshot.content,
                'hash': snapshot.content_hash,
                'timestamp': snapshot.captured_at,
            }
        return None

    def compare_snapshots(self, competitor_id: int, snapshot_type: str, new_data: Dict) -> Optional[Dict]:
        """对比快照检测变化"""
        last_snapshot = self.get_last_snapshot(competitor_id, snapshot_type)

        if not last_snapshot:
            # 第一次快照，保存但不触发告警
            self.save_snapshot(competitor_id, snapshot_type, new_data)
            return None

        old_data = last_snapshot['data']
        changes = None

        # 根据类型检测变化
        if snapshot_type == 'price':
            old_price = old_data.get('price', 0)
            new_price = new_data.get('price', 0)
            changes = self.detect_price_change(old_price, new_price)

        elif snapshot_type == 'sentiment':
            changes = self.detect_sentiment_change(old_data, new_data)

        elif snapshot_type == 'stock':
            old_stock = old_data.get('in_stock', False)
            new_stock = new_data.get('in_stock', False)
            changes = self.detect_stock_change(old_stock, new_stock)

        # 保存新快照
        self.save_snapshot(competitor_id, snapshot_type, new_data)

        return changes


# 全局服务实例
change_detection_service = ChangeDetectionService()
