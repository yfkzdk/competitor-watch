"""
一次性脚本：清除所有模拟生成的评论，从评论池重新加载
运行: python refresh_reviews.py
"""
import sys, os, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from datetime import datetime, timedelta
random.seed(42)

from app.core.database import SessionLocal
from app.core.models import UserReview
from app.services.review_pool import REVIEW_POOL

db = SessionLocal()

# 1. 删除所有评论
deleted = db.query(UserReview).delete()
db.commit()
print(f"已删除 {deleted} 条旧评论")

# 2. 从评论池全部写入（90条手写评论）
now = datetime.utcnow()
for i, r in enumerate(REVIEW_POOL):
    # 时间分散在过去45天内
    days_ago = (i * 2) % 45
    review_date = now - timedelta(days=days_ago, hours=random.randint(0, 23))
    db.add(UserReview(
        competitor_id=r["cid"],
        platform=r["platform"],
        author=r["author"],
        rating=r["rating"],
        content=r["content"],
        sentiment_score=r["sentiment"],
        review_date=review_date,
        collected_at=review_date + timedelta(hours=random.randint(1, 24)),
    ))

db.commit()

# 按竞品统计
from sqlalchemy import func
stats = db.query(UserReview.competitor_id, func.count(UserReview.id)).group_by(UserReview.competitor_id).all()
print("\n评论分布:")
for cid, count in stats:
    print(f"  竞品 {cid}: {count} 条")

db.close()
print(f"\n总计 {len(REVIEW_POOL)} 条真实风格评论已加载")
