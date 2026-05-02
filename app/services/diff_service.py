"""
Diff可视化服务 - 内容对比+高亮变化
参考: changedetection.io (placemarker diff, 时间线视图)
"""
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from sqlalchemy.orm import Session
from contextlib import contextmanager
from app.core.models import MonitoringSnapshot, Change


class DiffService:
    """Diff可视化服务"""

    def __init__(self, db: Session = None):
        self._injected_db = db

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

    @staticmethod
    def _snapshot_to_dict(snap: MonitoringSnapshot) -> Dict:
        return {
            "id": snap.id,
            "competitor_id": snap.competitor_id,
            "snapshot_type": snap.snapshot_type,
            "content": snap.content,
            "content_hash": snap.content_hash,
            "url": snap.url,
            "metadata": snap.metadata_,
            "captured_at": snap.captured_at.isoformat() if snap.captured_at else None,
        }

    def compare_snapshots(self, competitor_id: int,
                          snapshot_type: Optional[str] = None) -> Dict[str, Any]:
        """对比最近两次快照，返回差异详情"""
        with self._session() as db:
            q = (
                db.query(MonitoringSnapshot)
                .filter(MonitoringSnapshot.competitor_id == competitor_id)
            )
            if snapshot_type:
                q = q.filter(MonitoringSnapshot.snapshot_type == snapshot_type)
            rows = q.order_by(MonitoringSnapshot.captured_at.desc()).limit(2).all()

        if len(rows) < 2:
            return {
                'diff_count': 0,
                'message': '快照不足，无法对比' if len(rows) < 2 else '仅有一个快照',
                'has_change': False,
            }

        current = self._snapshot_to_dict(rows[0])
        previous = self._snapshot_to_dict(rows[1])

        try:
            current_data = json.loads(current['content']) if current['content'] else {}
            previous_data = json.loads(previous['content']) if previous['content'] else {}
        except (json.JSONDecodeError, TypeError):
            return {'diff_count': 0, 'message': '数据解析失败', 'has_change': False}

        diffs = self._compute_diff(previous_data, current_data)

        return {
            'competitor_id': competitor_id,
            'snapshot_type': current['snapshot_type'],
            'has_change': len(diffs) > 0,
            'diff_count': len(diffs),
            'diffs': diffs,
            'previous': {
                'timestamp': previous['captured_at'],
                'hash': previous['content_hash'],
                'data': previous_data,
            },
            'current': {
                'timestamp': current['captured_at'],
                'hash': current['content_hash'],
                'data': current_data,
            },
            'html_diff': self._generate_html_diff(diffs),
        }

    def compare_scrape_results(self, competitor_id: int,
                               limit: int = 2) -> Dict[str, Any]:
        """对比最近两次采集结果（基于monitoring_snapshots）"""
        with self._session() as db:
            rows = (
                db.query(MonitoringSnapshot)
                .filter(MonitoringSnapshot.competitor_id == competitor_id)
                .order_by(MonitoringSnapshot.captured_at.desc())
                .limit(limit)
                .all()
            )

        if len(rows) < 2:
            return {'diff_count': 0, 'message': '采集结果不足', 'has_change': False}

        current = self._snapshot_to_dict(rows[0])
        previous = self._snapshot_to_dict(rows[1])

        try:
            old_data = json.loads(previous.get('content') or '{}')
            new_data = json.loads(current.get('content') or '{}')
        except (json.JSONDecodeError, TypeError):
            old_data, new_data = {}, {}

        diffs = self._compute_diff(old_data, new_data)
        checksum_changed = current.get('content_hash') != previous.get('content_hash')

        return {
            'competitor_id': competitor_id,
            'has_change': len(diffs) > 0 or checksum_changed,
            'diff_count': len(diffs),
            'diffs': diffs,
            'checksum_changed': checksum_changed,
            'previous': {'timestamp': previous['captured_at'], 'checksum': previous.get('content_hash')},
            'current': {'timestamp': current['captured_at'], 'checksum': current.get('content_hash')},
            'html_diff': self._generate_html_diff(diffs),
        }

    def get_change_timeline(self, competitor_id: int,
                            days: int = 7) -> List[Dict[str, Any]]:
        """获取变化时间线（参考changedetection.io的history视图）"""
        since = datetime.now() - timedelta(days=days)
        with self._session() as db:
            rows = (
                db.query(Change)
                .filter(
                    Change.competitor_id == competitor_id,
                    Change.detected_at >= since,
                )
                .order_by(Change.detected_at.asc())
                .all()
            )

        timeline = []
        for r in rows:
            timeline.append({
                'timestamp': r.detected_at.isoformat() if r.detected_at else None,
                'field_name': r.field_name,
                'change_type': r.change_type,
                'severity': r.severity,
                'has_change': True,
                'old_value': r.old_value,
                'new_value': r.new_value,
            })
        return timeline

    def get_scrape_history(self, competitor_id: int,
                           limit: int = 20) -> List[Dict[str, Any]]:
        """获取采集历史（含变化标记）"""
        with self._session() as db:
            rows = (
                db.query(MonitoringSnapshot)
                .filter(MonitoringSnapshot.competitor_id == competitor_id)
                .order_by(MonitoringSnapshot.captured_at.desc())
                .limit(limit)
                .all()
            )

        results = []
        prev_hash = None
        for r in reversed(rows):
            entry = self._snapshot_to_dict(r)
            entry['is_change'] = entry.get('content_hash') != prev_hash if prev_hash else False
            if entry.get('content'):
                try:
                    entry['content'] = json.loads(entry['content'])
                except (json.JSONDecodeError, TypeError):
                    pass
            results.append(entry)
            prev_hash = entry.get('content_hash')

        return list(reversed(results))

    # ========== 内部方法 ==========

    def _compute_diff(self, old_data: Dict, new_data: Dict) -> List[Dict]:
        """计算两个字典的差异"""
        diffs = []
        all_keys = set(list(old_data.keys()) + list(new_data.keys()))

        for key in all_keys:
            old_val = old_data.get(key)
            new_val = new_data.get(key)

            if key not in old_data:
                diffs.append({
                    'field': key,
                    'type': 'added',
                    'old_value': None,
                    'new_value': new_val,
                })
            elif key not in new_data:
                diffs.append({
                    'field': key,
                    'type': 'removed',
                    'old_value': old_val,
                    'new_value': None,
                })
            elif old_val != new_val:
                diffs.append({
                    'field': key,
                    'type': 'modified',
                    'old_value': old_val,
                    'new_value': new_val,
                    'change_type': self._classify_change(key, old_val, new_val),
                })

        return diffs

    def _classify_change(self, field: str, old_val: Any, new_val: Any) -> str:
        """分类变化类型"""
        if field in ('price',) and isinstance(old_val, (int, float)) and isinstance(new_val, (int, float)):
            return 'price_up' if new_val > old_val else 'price_down'
        if field in ('in_stock', 'stock'):
            return 'back_in_stock' if new_val and not old_val else 'out_of_stock'
        return 'content_change'

    def _generate_html_diff(self, diffs: List[Dict]) -> str:
        """生成HTML格式的diff（参考changedetection.io的placemarker模式）"""
        if not diffs:
            return '<div class="diff-no-change">无变化</div>'

        lines = []
        for d in diffs:
            field = d.get('field', '')
            change_type = d.get('type', 'modified')
            old = d.get('old_value')
            new = d.get('new_value')

            if change_type == 'added':
                lines.append(
                    f'<div class="diff-added"><span class="diff-field">{field}</span>: '
                    f'<span class="diff-new">{new}</span></div>'
                )
            elif change_type == 'removed':
                lines.append(
                    f'<div class="diff-removed"><span class="diff-field">{field}</span>: '
                    f'<span class="diff-old">{old}</span></div>'
                )
            elif change_type == 'modified':
                pct = d.get('change_percentage')
                pct_str = f' ({pct:+.1f}%)' if pct is not None else ''
                lines.append(
                    f'<div class="diff-modified">'
                    f'<span class="diff-field">{field}</span>: '
                    f'<span class="diff-old">{old}</span> → '
                    f'<span class="diff-new">{new}</span>'
                    f'<span class="diff-pct">{pct_str}</span>'
                    f'</div>'
                )

        return '\n'.join(lines)


diff_service = DiffService()
