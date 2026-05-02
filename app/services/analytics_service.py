"""Analytics service — competitor analysis and insights. SQLAlchemy ORM."""
import statistics
from datetime import datetime, timedelta
from sqlalchemy import func, case
from sqlalchemy.orm import Session
from contextlib import contextmanager
from app.core.models import PriceHistory, UserReview, MonitoringLog, Competitor, Change


class AnalyticsService:
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

    def get_competitor_summary(self, competitor_id: int, days: int = 7):
        since = datetime.utcnow() - timedelta(days=days)
        with self._session() as db:
            # Price stats
            price_row = db.query(
                func.count(PriceHistory.id),
                func.avg(PriceHistory.price),
                func.min(PriceHistory.price),
                func.max(PriceHistory.price),
            ).filter(PriceHistory.competitor_id == competitor_id).first()

            # Price trend data
            recent_prices = db.query(PriceHistory).filter(
                PriceHistory.competitor_id == competitor_id,
                PriceHistory.recorded_at >= since,
            ).order_by(PriceHistory.recorded_at.asc()).all()
            price_trend = self._compute_trend_rows(
                [{"price": p.price, "recorded_at": p.recorded_at} for p in recent_prices], "price"
            )

            # Review sentiment
            review_row = db.query(
                func.count(UserReview.id),
                func.avg(UserReview.sentiment_score),
            ).filter(UserReview.competitor_id == competitor_id).first()

            # Monitoring stats
            monitor_row = db.query(
                func.count(MonitoringLog.id),
                func.sum(case((MonitoringLog.status == "success", 1), else_=0)),
                func.sum(case((MonitoringLog.status == "failed", 1), else_=0)),
                func.avg(MonitoringLog.response_time),
            ).filter(MonitoringLog.competitor_id == competitor_id).first()

            # Change count
            change_count = db.query(func.count(Change.id)).filter(
                Change.competitor_id == competitor_id
            ).scalar() or 0

        total, avg_price, min_price, max_price = price_row
        r_total, r_avg = review_row
        m_total, m_success, m_fail, m_avg_rt = monitor_row
        m_total = m_total or 0
        m_success = m_success or 0
        availability = round(m_success / m_total * 100, 1) if m_total > 0 else 0
        avg_sentiment = r_avg or 0

        return {
            "competitor_id": competitor_id,
            "price_analysis": {
                "total_products": total or 0,
                "avg_price": round(avg_price or 0, 2),
                "min_price": min_price or 0,
                "max_price": max_price or 0,
            },
            "price_trend": price_trend,
            "sentiment_analysis": {
                "total_reviews": r_total or 0,
                "avg_sentiment": round(avg_sentiment, 3),
                "sentiment_label": "positive" if avg_sentiment > 0.05 else ("negative" if avg_sentiment < -0.05 else "neutral"),
            },
            "monitoring_analysis": {
                "total_checks": m_total,
                "success_rate": availability,
                "avg_response_time": round(m_avg_rt or 0, 0),
            },
            "change_count": change_count,
            "anomaly_count": self._count_price_anomalies(competitor_id, days),
            "total_snapshots": m_total,
        }

    def _compute_trend_rows(self, rows, value_key):
        return self._compute_trend(rows, value_key)

    def _compute_trend(self, rows, value_key):
        if not rows or len(rows) < 2:
            return {"trend": "insufficient_data", "change_percentage": None,
                    "avg_value": 0, "values": [], "timestamps": [], "moving_average": []}
        values = [r[value_key] for r in rows]
        ts_key = next((k for k in rows[0] if k in ("recorded_at", "checked_at")), None)
        timestamps = [r.get(ts_key, "") for r in rows] if ts_key else []
        first, last = values[0], values[-1]
        change_pct = ((last - first) / first * 100) if first != 0 else 0
        if change_pct > 2:
            direction = "rising"
        elif change_pct < -2:
            direction = "falling"
        else:
            direction = "stable"
        ma = []
        for i in range(len(values)):
            start = max(0, i - 2)
            window = values[start:i + 3]
            ma.append(round(sum(window) / len(window), 2))
        return {
            "trend": direction,
            "change_percentage": round(change_pct, 1),
            "avg_value": round(sum(values) / len(values), 2),
            "values": values,
            "timestamps": timestamps,
            "moving_average": ma,
        }

    def _count_price_anomalies(self, competitor_id: int, days: int = 30):
        since = datetime.utcnow() - timedelta(days=days)
        with self._session() as db:
            rows = db.query(PriceHistory.price).filter(
                PriceHistory.competitor_id == competitor_id,
                PriceHistory.recorded_at >= since,
            ).order_by(PriceHistory.recorded_at).all()
        if len(rows) < 3:
            return 0
        prices = [r.price for r in rows]
        mean = statistics.mean(prices)
        stdev = statistics.stdev(prices)
        if stdev == 0:
            return 0
        return sum(1 for p in prices if abs(p - mean) / stdev > 2)

    def get_trend_analysis(self, competitor_id: int, metric: str = "price", days: int = 7):
        since = datetime.utcnow() - timedelta(days=days)
        with self._session() as db:
            if metric == "price":
                rows = db.query(PriceHistory).filter(
                    PriceHistory.competitor_id == competitor_id,
                    PriceHistory.recorded_at >= since,
                ).order_by(PriceHistory.recorded_at.asc()).all()
                return self._compute_trend_rows(
                    [{"price": r.price, "recorded_at": r.recorded_at} for r in rows], "price"
                )
            rows = db.query(MonitoringLog).filter(
                MonitoringLog.competitor_id == competitor_id,
                MonitoringLog.checked_at >= since,
            ).order_by(MonitoringLog.checked_at.asc()).all()
            return self._compute_trend_rows(
                [{"response_time": r.response_time, "checked_at": r.checked_at} for r in rows], "response_time"
            )

    def detect_anomalies(self, competitor_id: int, metric: str = "price",
                         days: int = 30, sensitivity: float = 2.0):
        since = datetime.utcnow() - timedelta(days=days)
        with self._session() as db:
            if metric == "price":
                rows = db.query(PriceHistory).filter(
                    PriceHistory.competitor_id == competitor_id,
                    PriceHistory.recorded_at >= since,
                ).order_by(PriceHistory.recorded_at).all()
                values = [r.price for r in rows]
                timestamps = [r.recorded_at for r in rows]
            else:
                rows = db.query(MonitoringLog).filter(
                    MonitoringLog.competitor_id == competitor_id,
                    MonitoringLog.checked_at >= since,
                ).order_by(MonitoringLog.checked_at).all()
                values = [r.response_time for r in rows]
                timestamps = [r.checked_at for r in rows]

        if len(values) < 3:
            return []
        mean = statistics.mean(values)
        stdev = statistics.stdev(values)
        if stdev == 0:
            return []
        anomalies = []
        for i, (v, ts) in enumerate(zip(values, timestamps)):
            z = abs(v - mean) / stdev
            if z > sensitivity:
                anomalies.append({"index": i, "value": v, "z_score": round(z, 2), "timestamp": ts})
        return anomalies

    def get_correlation(self, competitor_id_1: int, competitor_id_2: int,
                        metric: str = "price", days: int = 30):
        since = datetime.utcnow() - timedelta(days=days)
        with self._session() as db:
            if metric == "price":
                rows1 = db.query(
                    func.avg(PriceHistory.price), func.date(PriceHistory.recorded_at)
                ).filter(
                    PriceHistory.competitor_id == competitor_id_1,
                    PriceHistory.recorded_at >= since,
                ).group_by(func.date(PriceHistory.recorded_at)).order_by(func.date(PriceHistory.recorded_at)).all()
                rows2 = db.query(
                    func.avg(PriceHistory.price), func.date(PriceHistory.recorded_at)
                ).filter(
                    PriceHistory.competitor_id == competitor_id_2,
                    PriceHistory.recorded_at >= since,
                ).group_by(func.date(PriceHistory.recorded_at)).order_by(func.date(PriceHistory.recorded_at)).all()
            else:
                rows1 = db.query(
                    func.avg(MonitoringLog.response_time), func.date(MonitoringLog.checked_at)
                ).filter(
                    MonitoringLog.competitor_id == competitor_id_1,
                    MonitoringLog.checked_at >= since,
                ).group_by(func.date(MonitoringLog.checked_at)).order_by(func.date(MonitoringLog.checked_at)).all()
                rows2 = db.query(
                    func.avg(MonitoringLog.response_time), func.date(MonitoringLog.checked_at)
                ).filter(
                    MonitoringLog.competitor_id == competitor_id_2,
                    MonitoringLog.checked_at >= since,
                ).group_by(func.date(MonitoringLog.checked_at)).order_by(func.date(MonitoringLog.checked_at)).all()

        map1 = {str(d): v for v, d in rows1}
        map2 = {str(d): v for v, d in rows2}
        common = set(map1.keys()) & set(map2.keys())
        if len(common) < 3:
            return {"correlation": 0, "competitor_1": competitor_id_1,
                    "competitor_2": competitor_id_2, "data_points": len(common)}
        v1 = [map1[d] for d in sorted(common)]
        v2 = [map2[d] for d in sorted(common)]
        n = len(v1)
        m1, m2 = sum(v1) / n, sum(v2) / n
        cov = sum((a - m1) * (b - m2) for a, b in zip(v1, v2)) / n
        s1 = (sum((a - m1) ** 2 for a in v1) / n) ** 0.5
        s2 = (sum((b - m2) ** 2 for b in v2) / n) ** 0.5
        corr = cov / (s1 * s2) if s1 and s2 else 0
        return {"correlation": round(corr, 3), "competitor_1": competitor_id_1,
                "competitor_2": competitor_id_2, "data_points": len(common)}

    def get_all_correlations(self, metric: str = "price", days: int = 30):
        with self._session() as db:
            comps = db.query(Competitor.id, Competitor.name).all()
        if not comps:
            return []
        ids = [c.id for c in comps]
        names = {c.id: c.name for c in comps}
        matrix = []
        for i, id1 in enumerate(ids):
            for j, id2 in enumerate(ids):
                if i >= j:
                    continue
                result = self.get_correlation(id1, id2, metric, days)
                matrix.append({
                    "competitor_1": {"id": id1, "name": names[id1]},
                    "competitor_2": {"id": id2, "name": names[id2]},
                    "correlation": result["correlation"],
                })
        return matrix

    def get_comparison(self, competitor_ids: list):
        return [self.get_competitor_summary(cid) for cid in competitor_ids]


analytics_service = AnalyticsService()
