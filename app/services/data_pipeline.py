#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据闭环管道 — 采集→检测→持久化→告警

参考 changedetection.io 的四步流水线模式:
  1. FETCH: 采集数据
  2. DETECT: 变更检测（checksum + diff）
  3. PERSIST: 持久化到数据库（原子写入）
  4. NOTIFY: 评估规则 → 触发告警

参考 Huginn 的 Event 传播模式:
  Event 作为唯一通信机制，驱动下游动作
"""

import json
import hashlib
import logging
from datetime import datetime
from typing import Dict, List, Optional
from contextlib import contextmanager

from sqlalchemy.orm import Session

from app.core.models import (
    Competitor, MonitoringLog, MonitoringSnapshot, Change,
    AnalysisReport, AlertRule,
)

logger = logging.getLogger(__name__)


class DataPipeline:
    """数据闭环管道 — 采集→检测→持久化→告警"""

    def __init__(self, db: Session = None):
        self._injected_db = db
        self._alert_service = None

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
    def alert_service(self):
        if self._alert_service is None:
            from app.services.alert_service import alert_service
            self._alert_service = alert_service
        return self._alert_service

    def run(self, competitor_id: int, fetch_result: Dict) -> Dict:
        """
        执行完整数据闭环管道

        Args:
            competitor_id: 竞品ID
            fetch_result: fetch_competitor_data() 返回的结果

        Returns:
            管道执行结果
        """
        pipeline_result = {
            "competitor_id": competitor_id,
            "fetch_events": 0,
            "changes_detected": [],
            "alerts_triggered": 0,
            "timestamp": datetime.now().isoformat(),
        }

        # STEP 1: PERSIST — 将采集事件写入 monitoring_logs
        events = fetch_result.get("events", [])
        pipeline_result["fetch_events"] = len(events)

        if events:
            self._persist_events_batch(competitor_id, events)

        # STEP 2: PERSIST METRICS — 更新竞品指标
        metrics = fetch_result.get("metrics", {})
        if metrics:
            self._persist_metrics(competitor_id, metrics)

        # STEP 3: DETECT — 变更检测（checksum 对比）
        checksum = self._compute_checksum(fetch_result)
        changes = self._detect_changes(competitor_id, checksum, fetch_result)
        pipeline_result["changes_detected"] = changes

        # STEP 4: PERSIST CHECKSUM — 始终记录 checksum 用于下次对比
        self._persist_checksum(competitor_id, checksum)

        # STEP 5: PERSIST CHANGES — 将变更写入 changes 表
        for change in changes:
            self._persist_change(competitor_id, change)

        # STEP 5: NOTIFY — 评估告警规则并触发
        for change in changes:
            alert_id = self._evaluate_and_alert(competitor_id, change)
            if alert_id:
                pipeline_result["alerts_triggered"] += 1

        # STEP 6: PERSIST ANALYSIS — 记录分析报告
        if events or changes:
            self._persist_analysis_report(competitor_id, fetch_result, changes)

        logger.info(
            f"[Pipeline] competitor_id={competitor_id}: "
            f"events={len(events)}, changes={len(changes)}, alerts={pipeline_result['alerts_triggered']}"
        )

        return pipeline_result

    def _persist_events_batch(self, competitor_id: int, events: List[Dict]):
        """将事件批量写入 monitoring_logs 表"""
        with self._session() as db:
            for event in events:
                event_data = json.dumps(event.get("data", {}), ensure_ascii=False)
                log = MonitoringLog(
                    competitor_id=competitor_id,
                    status="success",
                    response_time=0.5,
                    error_message="",
                    url=event.get("source", ""),
                    content_hash="",
                    content_length=len(event_data),
                    monitoring_type="pipeline",
                    details=event.get("data"),
                    checked_at=datetime.utcnow(),
                )
                db.add(log)

    def _persist_metrics(self, competitor_id: int, metrics: Dict):
        """更新竞品指标到 competitors 表"""
        metric_to_column = {
            "innovation_velocity": "innovation_velocity",
            "feature_count": "feature_count",
            "security_mentions": "security_mentions",
            "price_index": "price_index",
            "market_share": "market_share",
            "user_rating": "user_rating",
            "growth": "growth",
        }

        update_kwargs = {}
        for metric_key, column_name in metric_to_column.items():
            if metric_key in metrics:
                update_kwargs[column_name] = metrics[metric_key]

        if not update_kwargs:
            return

        update_kwargs["updated_at"] = datetime.utcnow()

        with self._session() as db:
            db.query(Competitor).filter(Competitor.id == competitor_id).update(
                update_kwargs, synchronize_session=False
            )

    def _compute_checksum(self, fetch_result: Dict) -> str:
        """计算采集结果的 checksum（参考 changedetection.io 的 MD5 对比）"""
        key_data = {
            "events": [(e.get("type", ""), e.get("title", "")) for e in fetch_result.get("events", [])],
            "metrics": fetch_result.get("metrics", {}),
        }
        data_str = json.dumps(key_data, sort_keys=True, ensure_ascii=False)
        return hashlib.md5(data_str.encode("utf-8")).hexdigest()

    def _detect_changes(self, competitor_id: int, new_checksum: str, fetch_result: Dict) -> List[Dict]:
        """
        变更检测 — 对比新旧 checksum

        参考 changedetection.io: previous_md5 != fetched_md5 → changed_detected = True
        """
        changes = []

        # 获取上次 checksum（从 monitoring_snapshots 或 changes 表）
        old_checksum = self._get_last_checksum(competitor_id)

        # checksum 变化 → 有变更
        if old_checksum and old_checksum != new_checksum:
            changes.append({
                "type": "content_changed",
                "severity": "P2",
                "old_checksum": old_checksum,
                "new_checksum": new_checksum,
                "message": f"竞品内容发生变化 (checksum: {old_checksum[:8]} → {new_checksum[:8]})",
            })

        # 价格变化检测
        price_events = [e for e in fetch_result.get("events", []) if e.get("type") == "price_detected"]
        if price_events:
            changes.append({
                "type": "price_change",
                "severity": "P1",
                "prices": price_events,
                "message": f"检测到 {len(price_events)} 个价格信息",
            })

        # 版本变化检测
        version_events = [e for e in fetch_result.get("events", []) if e.get("type") == "version_detected"]
        if version_events:
            changes.append({
                "type": "version_change",
                "severity": "P2",
                "versions": version_events,
                "message": f"检测到新版本: {version_events[0].get('title', '')}",
            })

        return changes

    def _get_last_checksum(self, competitor_id: int) -> str:
        """获取上次采集的 checksum"""
        try:
            with self._session() as db:
                snapshot = (
                    db.query(MonitoringSnapshot.content_hash)
                    .filter(
                        MonitoringSnapshot.competitor_id == competitor_id,
                        MonitoringSnapshot.snapshot_type == "checksum",
                        MonitoringSnapshot.content_hash.isnot(None),
                    )
                    .order_by(MonitoringSnapshot.captured_at.desc())
                    .first()
                )
                if snapshot and snapshot.content_hash:
                    return snapshot.content_hash
        except Exception:
            pass

        return ""

    def _persist_checksum(self, competitor_id: int, checksum: str):
        """记录 checksum 到 monitoring_snapshots，用于下次变更检测"""
        try:
            with self._session() as db:
                snapshot = MonitoringSnapshot(
                    competitor_id=competitor_id,
                    snapshot_type="checksum",
                    content="{}",
                    content_hash=checksum,
                    url="",
                    captured_at=datetime.utcnow(),
                )
                db.add(snapshot)
        except Exception:
            pass

    def _persist_change(self, competitor_id: int, change: Dict):
        """将变更写入 changes 表"""
        change_type = change.get("type", "unknown")
        old_value = change.get("old_checksum", "")
        new_value = change.get("new_checksum", "")

        # 价格/版本变更的值
        if change_type == "price_change":
            prices = change.get("prices", [])
            new_value = json.dumps(
                [p.get("data", {}) for p in prices],
                ensure_ascii=False,
            )
        elif change_type == "version_change":
            versions = change.get("versions", [])
            new_value = json.dumps(
                [v.get("title", "") for v in versions],
                ensure_ascii=False,
            )

        with self._session() as db:
            change_record = Change(
                competitor_id=competitor_id,
                field_name=change_type,
                old_value=old_value,
                new_value=new_value,
                change_type=change_type,
                severity=change.get("severity", "P2"),
                detected_at=datetime.utcnow(),
                is_read=False,
            )
            db.add(change_record)

    def _evaluate_and_alert(self, competitor_id: int, change: Dict) -> Optional[int]:
        """
        评估告警规则并触发告警

        参考 Huginn TriggerAgent: rules → match → create_event → propagate
        参考 changedetection.io: changed_detected → send_content_changed_notification
        """
        # 获取该竞品的告警规则
        try:
            with self._session() as db:
                rules = (
                    db.query(AlertRule)
                    .filter(
                        AlertRule.competitor_id == competitor_id,
                        AlertRule.is_active == True,
                    )
                    .all()
                )
                # Convert to list of dicts to match legacy interface
                rules_data = [
                    {
                        "rule_type": r.rule_type,
                        "id": r.id,
                        "competitor_id": r.competitor_id,
                    }
                    for r in rules
                ]
        except Exception:
            rules_data = []

        for rule in rules_data:
            rule_type = rule.get("rule_type", "")

            # 价格变化告警
            if rule_type == "price_change" and change.get("type") == "price_change":
                return self.alert_service.trigger_alert(
                    competitor_id=competitor_id,
                    alert_type="price_change",
                    severity=change.get("severity", "P1"),
                    message=change.get("message", ""),
                    metadata=change,
                )

            # 内容变化告警
            if rule_type == "content_change" and change.get("type") == "content_changed":
                return self.alert_service.trigger_alert(
                    competitor_id=competitor_id,
                    alert_type="content_changed",
                    severity=change.get("severity", "P2"),
                    message=change.get("message", ""),
                    metadata=change,
                )

            # 版本变化告警
            if rule_type == "version_change" and change.get("type") == "version_change":
                return self.alert_service.trigger_alert(
                    competitor_id=competitor_id,
                    alert_type="version_change",
                    severity=change.get("severity", "P2"),
                    message=change.get("message", ""),
                    metadata=change,
                )

        # 无匹配规则时，对 P0/P1 级别变化自动告警
        if change.get("severity") in ("P0", "P1"):
            return self.alert_service.trigger_alert(
                competitor_id=competitor_id,
                alert_type=change.get("type", "unknown"),
                severity=change.get("severity", "P1"),
                message=change.get("message", "检测到重要变化"),
                metadata=change,
            )

        return None

    def _persist_analysis_report(self, competitor_id: int, fetch_result: Dict, changes: List[Dict]):
        """将分析结果写入 analysis_reports 表"""
        insight = f"采集 {len(fetch_result.get('events', []))} 个事件, 检测到 {len(changes)} 个变更"

        with self._session() as db:
            report = AnalysisReport(
                competitor_id=competitor_id,
                report_type="pipeline_auto",
                title=None,
                summary=insight,
                content=json.dumps(fetch_result.get("events", [])[:10], ensure_ascii=False),
                confidence_score=0.8,
                recommendations=json.dumps(
                    [{"type": c.get("type"), "action": "review"} for c in changes],
                    ensure_ascii=False,
                ),
                model_used="data_pipeline_v1",
                created_at=datetime.utcnow(),
            )
            db.add(report)


# 全局实例
data_pipeline = DataPipeline()
