"""Price tracking and comparison service."""
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from contextlib import contextmanager
from app.core.models import PriceHistory, Competitor


class PriceService:
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
    def _price_to_dict(ph: PriceHistory, competitor_name: str = None) -> dict:
        result = {
            "id": ph.id,
            "competitor_id": ph.competitor_id,
            "product_name": ph.product_name,
            "price": ph.price,
            "original_price": ph.original_price,
            "currency": ph.currency,
            "source": ph.source,
            "recorded_at": ph.recorded_at.isoformat() if ph.recorded_at else None,
        }
        if competitor_name is not None:
            result["competitor_name"] = competitor_name
        return result

    def get_price_history(self, competitor_id: int, product_name: str = None,
                          start_date: str = None, end_date: str = None,
                          limit: int = 100):
        from sqlalchemy import func
        with self._session() as db:
            q = db.query(PriceHistory).filter(
                PriceHistory.competitor_id == competitor_id,
            )
            if product_name:
                q = q.filter(PriceHistory.product_name.like(f"%{product_name}%"))
            if start_date:
                q = q.filter(PriceHistory.recorded_at >= start_date)
            if end_date:
                q = q.filter(PriceHistory.recorded_at <= end_date)

            # statistics
            stats = q.with_entities(
                func.count(PriceHistory.id),
                func.avg(PriceHistory.price),
                func.min(PriceHistory.price),
                func.max(PriceHistory.price),
            ).first()

            rows = q.order_by(PriceHistory.recorded_at.desc()).limit(limit).all()
            return {
                "competitor_id": competitor_id,
                "prices": [self._price_to_dict(r) for r in rows],
                "statistics": {
                    "count": stats[0] or 0,
                    "avg_price": round(stats[1] or 0, 2),
                    "min_price": round(stats[2] or 0, 2),
                    "max_price": round(stats[3] or 0, 2),
                },
            }

    def get_latest_prices(self, competitor_id: int):
        with self._session() as db:
            rows = (
                db.query(PriceHistory)
                .filter(PriceHistory.competitor_id == competitor_id)
                .order_by(PriceHistory.recorded_at.desc())
                .limit(10)
                .all()
            )
            return [self._price_to_dict(r) for r in rows]

    def get_price_comparison(self, product_name: str):
        with self._session() as db:
            rows = (
                db.query(PriceHistory, Competitor.name)
                .join(Competitor, PriceHistory.competitor_id == Competitor.id)
                .filter(PriceHistory.product_name.like(f"%{product_name}%"))
                .order_by(PriceHistory.price.asc())
                .all()
            )
            return [self._price_to_dict(ph, competitor_name=name) for ph, name in rows]

    def compare_prices(self, competitor_ids: list, product_name: str):
        if not competitor_ids:
            return {"comparison": [], "analysis": {}}
        with self._session() as db:
            from sqlalchemy import func
            rows = (
                db.query(PriceHistory, Competitor.name)
                .join(Competitor, PriceHistory.competitor_id == Competitor.id)
                .filter(
                    PriceHistory.competitor_id.in_(competitor_ids),
                    PriceHistory.product_name.like(f"%{product_name}%"),
                )
                .order_by(PriceHistory.price.asc())
                .all()
            )
            comparison = [self._price_to_dict(ph, competitor_name=name) for ph, name in rows]
            prices = [ph.price for ph, _ in rows]
            analysis = {}
            if prices:
                analysis = {
                    "lowest": min(prices),
                    "highest": max(prices),
                    "average": round(sum(prices) / len(prices), 2),
                    "data_points": len(prices),
                }
            return {"comparison": comparison, "analysis": analysis}

    def predict_price(self, competitor_id: int, product_name: str,
                      days: int = 7, historical_days: int = 90):
        since = datetime.now() - timedelta(days=historical_days)
        with self._session() as db:
            rows = (
                db.query(PriceHistory.price, PriceHistory.recorded_at)
                .filter(
                    PriceHistory.competitor_id == competitor_id,
                    PriceHistory.product_name.like(f"%{product_name}%"),
                    PriceHistory.recorded_at >= since,
                )
                .order_by(PriceHistory.recorded_at.asc())
                .all()
            )
        if len(rows) < 3:
            return {"success": False, "error": "历史数据不足，至少需要3条记录"}

        prices = [r[0] for r in rows]
        n = len(prices)
        avg = sum(prices) / n
        recent = prices[-min(7, n):]
        recent_avg = sum(recent) / len(recent)
        trend_slope = (recent_avg - avg) / max(n, 1)

        predictions = []
        for i in range(1, days + 1):
            pred = recent_avg + trend_slope * i
            margin = (max(prices) - min(prices)) * 0.1 * (i / days)
            predictions.append({
                "date": (datetime.now() + timedelta(days=i)).strftime("%Y-%m-%d"),
                "predicted_price": round(pred, 2),
                "confidence_upper": round(pred + margin, 2),
                "confidence_lower": round(pred - margin, 2),
            })

        historical = [{"timestamp": r[1], "price": r[0]} for r in rows[-30:]]
        return {
            "success": True,
            "data": {"predictions": predictions, "historical": historical},
        }

    def add_price_record(self, competitor_id: int, product_name: str,
                         price: float, original_price: float = None,
                         currency: str = "CNY", source: str = ""):
        if original_price is None:
            original_price = price
        with self._session() as db:
            record = PriceHistory(
                competitor_id=competitor_id,
                product_name=product_name,
                price=price,
                original_price=original_price,
                currency=currency,
                source=source,
                recorded_at=datetime.utcnow(),
            )
            db.add(record)
            db.flush()
            db.refresh(record)
            return record.id


price_service = PriceService()
