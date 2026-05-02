"""Review analysis service — sentiment and review data operations."""
from typing import Optional
from datetime import datetime, timedelta
from sqlalchemy import func, case
from sqlalchemy.orm import Session
from contextlib import contextmanager
from app.core.models import UserReview


def _classify_sentiment(score: float) -> str:
    if score > 0.05:
        return "positive"
    elif score < -0.05:
        return "negative"
    return "neutral"


class ReviewService:
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
    def _review_to_dict(review: UserReview) -> dict:
        return {
            "id": review.id,
            "competitor_id": review.competitor_id,
            "platform": review.platform,
            "author": review.author,
            "rating": review.rating,
            "content": review.content,
            "sentiment_score": review.sentiment_score,
            "review_date": review.review_date.isoformat() if review.review_date else None,
            "collected_at": review.collected_at.isoformat() if review.collected_at else None,
        }

    def get_reviews(self, competitor_id: int, limit: int = 50, offset: int = 0):
        with self._session() as db:
            rows = (
                db.query(UserReview)
                .filter(UserReview.competitor_id == competitor_id)
                .order_by(UserReview.review_date.desc())
                .offset(offset)
                .limit(limit)
                .all()
            )
            return [self._review_to_dict(r) for r in rows]

    def get_sentiment_summary(self, competitor_id: int, days: int = 30):
        since = datetime.now() - timedelta(days=days)
        with self._session() as db:
            rows = (
                db.query(UserReview.sentiment_score)
                .filter(
                    UserReview.competitor_id == competitor_id,
                    UserReview.review_date >= since,
                )
                .all()
            )
        if not rows:
            return {
                "competitor_id": competitor_id,
                "total_reviews": 0,
                "average_score": 0,
                "sentiment_distribution": {"positive": 0, "neutral": 0, "negative": 0},
            }

        scores = [r[0] for r in rows if r[0] is not None]
        dist = {"positive": 0, "neutral": 0, "negative": 0}
        for s in scores:
            dist[_classify_sentiment(s)] += 1

        return {
            "competitor_id": competitor_id,
            "total_reviews": len(scores),
            "average_score": round(sum(scores) / len(scores), 3) if scores else 0,
            "average_sentiment_score": round(sum(scores) / len(scores), 3) if scores else 0,
            "sentiment_distribution": dist,
        }

    def get_sentiment_trend(self, competitor_id: int, days: int = 30):
        since = datetime.now() - timedelta(days=days)
        with self._session() as db:
            rows = (
                db.query(
                    func.date(UserReview.review_date).label("period"),
                    func.avg(UserReview.sentiment_score).label("avg_score"),
                    func.sum(case((UserReview.sentiment_score > 0.05, 1), else_=0)).label("positive_count"),
                    func.sum(case((UserReview.sentiment_score.between(-0.05, 0.05), 1), else_=0)).label("neutral_count"),
                    func.sum(case((UserReview.sentiment_score < -0.05, 1), else_=0)).label("negative_count"),
                    func.count().label("total_count"),
                )
                .filter(
                    UserReview.competitor_id == competitor_id,
                    UserReview.review_date >= since,
                )
                .group_by(func.date(UserReview.review_date))
                .order_by(func.date(UserReview.review_date))
                .all()
            )
        trend = []
        for r in rows:
            trend.append({
                "date": str(r.period) if r.period else None,
                "avg_score": round(r.avg_score, 3) if r.avg_score is not None else 0,
                "positive_count": r.positive_count or 0,
                "neutral_count": r.neutral_count or 0,
                "negative_count": r.negative_count or 0,
                "total_count": r.total_count,
            })
        return {
            "competitor_id": competitor_id,
            "days": days,
            "trend": trend,
        }

    def get_review_stats(self, competitor_id: Optional[int] = None):
        with self._session() as db:
            if competitor_id:
                row = (
                    db.query(
                        func.count(UserReview.id).label("total"),
                        func.avg(UserReview.sentiment_score).label("avg_score"),
                    )
                    .filter(UserReview.competitor_id == competitor_id)
                    .first()
                )
            else:
                row = (
                    db.query(
                        func.count(UserReview.id).label("total"),
                        func.avg(UserReview.sentiment_score).label("avg_score"),
                    )
                    .first()
                )
        if row:
            return {
                "total_reviews": row.total,
                "average_score": round(row.avg_score, 3) if row.avg_score else 0,
            }
        return {"total_reviews": 0, "average_score": 0}


review_service = ReviewService()
