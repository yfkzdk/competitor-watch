"""
竞品多维对比服务 — 生成 N(竞品) × M(指标) 矩阵
"""
from typing import Dict, List, Optional
from sqlalchemy.orm import Session
from contextlib import contextmanager
from app.core.models import Competitor


class ComparisonService:
    """多维竞品对比"""

    METRIC_COLUMNS = [
        "innovation_velocity",
        "feature_count",
        "security_mentions",
        "market_share",
        "price_index",
        "user_rating",
        "growth",
    ]

    METRIC_LABELS = {
        "innovation_velocity": "创新活跃度",
        "feature_count": "功能数量",
        "security_mentions": "安全提及",
        "market_share": "市场份额",
        "price_index": "价格指数",
        "user_rating": "用户评分",
        "growth": "增长率",
    }

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
    def _comp_to_dict(comp: Competitor) -> Dict:
        return {
            "id": comp.id,
            "name": comp.name,
            "url": comp.url,
            "category": comp.category or "未分类",
            "status": comp.status or "active",
            "priority": comp.priority or "medium",
            "description": comp.description or "",
            "type": comp.type or "all",
            "frequency": comp.frequency or "15",
            "market_share": comp.market_share or 0,
            "price_index": comp.price_index or 90,
            "user_rating": comp.user_rating or 4.0,
            "growth": comp.growth or 0,
            "feature_count": comp.feature_count or 0,
            "innovation_velocity": comp.innovation_velocity or 0,
            "security_mentions": comp.security_mentions or 0,
            "last_checked": comp.last_checked.isoformat() if comp.last_checked else None,
            "created_at": comp.created_at.isoformat() if comp.created_at else None,
            "updated_at": comp.updated_at.isoformat() if comp.updated_at else None,
        }

    def get_comparison_matrix(
        self,
        competitor_ids: Optional[List[int]] = None,
        metrics: Optional[List[str]] = None,
    ) -> Dict:
        """
        生成竞品对比矩阵

        Returns:
            {
                "competitors": [{"id": 1, "name": "阿里云"}, ...],
                "metrics": ["innovation_velocity", ...],
                "matrix": {"1": {"innovation_velocity": 0.85, ...}, ...},
                "ranking": {"innovation_velocity": [{"id": 1, "value": 0.85}, ...]},
                "summary": {"best": {"innovation_velocity": {"id": 1, "name": "阿里云", "value": 0.85}}, ...}
            }
        """
        selected_metrics = metrics or self.METRIC_COLUMNS

        with self._session() as db:
            if competitor_ids:
                rows = (
                    db.query(Competitor)
                    .filter(Competitor.id.in_(competitor_ids))
                    .order_by(Competitor.id)
                    .all()
                )
            else:
                rows = db.query(Competitor).order_by(Competitor.id).all()

        competitors = []
        matrix = {}
        for comp_row in rows:
            comp = self._comp_to_dict(comp_row)
            competitors.append({"id": comp["id"], "name": comp["name"]})
            matrix[str(comp["id"])] = {
                m: (comp.get(m) or 0) for m in selected_metrics
            }

        # 排名
        ranking = {}
        for metric in selected_metrics:
            values = [
                {"id": c["id"], "name": c["name"], "value": matrix[str(c["id"])][metric]}
                for c in competitors
            ]
            ranking[metric] = sorted(values, key=lambda x: x["value"], reverse=True)

        # 最优项
        summary = {"best": {}}
        for metric in selected_metrics:
            if ranking[metric]:
                best = ranking[metric][0]
                summary["best"][metric] = best

        return {
            "competitors": competitors,
            "metrics": selected_metrics,
            "metric_labels": {m: self.METRIC_LABELS.get(m, m) for m in selected_metrics},
            "matrix": matrix,
            "ranking": ranking,
            "summary": summary,
        }

    def get_radar_data(self, competitor_ids: Optional[List[int]] = None) -> Dict:
        """
        生成雷达图数据（归一化到 0-100）

        Returns:
            {
                "indicators": [{"name": "创新活跃度", "max": 100}, ...],
                "series": [{"name": "阿里云", "value": [85, 60, ...]}, ...]
            }
        """
        matrix_result = self.get_comparison_matrix(competitor_ids)
        metrics = matrix_result["metrics"]
        matrix = matrix_result["matrix"]

        # 归一化：每个指标映射到 0-100
        normalized = {}
        for metric in metrics:
            values = [matrix[str(c["id"])][metric] for c in matrix_result["competitors"]]
            min_v = min(values) if values else 0
            max_v = max(values) if values else 1
            range_v = max_v - min_v if max_v != min_v else 1

            for c in matrix_result["competitors"]:
                cid = str(c["id"])
                if cid not in normalized:
                    normalized[cid] = []
                val = matrix[cid][metric]
                norm = ((val - min_v) / range_v) * 100 if range_v else 50
                normalized[cid].append(round(norm, 1))

        indicators = [
            {"name": matrix_result["metric_labels"].get(m, m), "max": 100}
            for m in metrics
        ]

        series = [
            {
                "name": c["name"],
                "value": normalized[str(c["id"])],
            }
            for c in matrix_result["competitors"]
        ]

        return {"indicators": indicators, "series": series}


comparison_service = ComparisonService()
