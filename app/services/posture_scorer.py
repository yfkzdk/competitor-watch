"""
竞争态势评分引擎 — 5维抽象评估

维度:
  1. 攻击性 (Aggressiveness) — 降价频率 × 功能发布速度
  2. 稳定度 (Stability)     — 价格波动率 × 评论情感一致性
  3. 创新力 (Innovation)    — 功能增长 × 新技术关键词密度
  4. 客户口碑 (Sentiment)   — 情感趋势 × 评论量增长率
  5. 威胁等级 (Threat)      — 加权综合，按市场份额调节

所有维度归一化到 0-100，同时返回评分依据（evidence）供前端展示。
"""
import logging
import math
from datetime import datetime, timedelta
from typing import Any, Dict, List

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.models import PriceHistory, Change, UserReview, Competitor

logger = logging.getLogger(__name__)


def _score_aggressiveness(comp_id: int, db: Session) -> tuple:
    """攻击性评分 — 降价频率 + 功能发布速度"""
    cutoff = datetime.utcnow() - timedelta(days=30)

    # 近期价格变化（30天）
    price_rows = (
        db.query(PriceHistory.price)
        .filter(
            PriceHistory.competitor_id == comp_id,
            PriceHistory.recorded_at >= cutoff,
        )
        .order_by(PriceHistory.recorded_at)
        .all()
    )
    prices = [r[0] for r in price_rows] if price_rows else []

    # 降价次数
    price_drops = sum(1 for i in range(1, len(prices)) if prices[i] < prices[i - 1])
    drop_ratio = min(price_drops / max(len(prices) - 1, 1), 1.0) if len(prices) > 1 else 0

    # 功能发布频率（30天内的 feature_update 变更）
    feature_count = (
        db.query(func.count(Change.id))
        .filter(
            Change.competitor_id == comp_id,
            Change.change_type.in_(['feature_update', 'version_change']),
            Change.detected_at >= cutoff,
        )
        .scalar()
    ) or 0
    feature_vel = min(feature_count / 10, 1.0)  # 10个功能变更/月 = 满分

    score = round(drop_ratio * 50 + feature_vel * 50)
    evidence = f"30天内降价{price_drops}次，功能/版本变更{feature_count}次"
    return score, evidence


def _score_stability(comp_id: int, db: Session) -> tuple:
    """稳定度评分 — 价格波动 + 情感一致性"""
    cutoff = datetime.utcnow() - timedelta(days=30)

    # 价格波动率
    price_rows = (
        db.query(PriceHistory.price)
        .filter(
            PriceHistory.competitor_id == comp_id,
            PriceHistory.recorded_at >= cutoff,
        )
        .order_by(PriceHistory.recorded_at)
        .all()
    )
    prices = [r[0] for r in price_rows] if price_rows else []
    if len(prices) >= 3:
        mean = sum(prices) / len(prices)
        std = math.sqrt(sum((p - mean) ** 2 for p in prices) / len(prices))
        cv = std / mean if mean > 0 else 2  # 变异系数
        price_stability = max(0, min(1, 1 - cv * 3))  # cv=0 → 100分, cv=0.33 → 0分
    else:
        price_stability = 0.5
        cv = 0

    # 评论情感一致性（标准差越小越稳定）
    sent_row = (
        db.query(
            func.avg(UserReview.sentiment_score).label("avg_s"),
            func.count(UserReview.id).label("cnt"),
        )
        .filter(
            UserReview.competitor_id == comp_id,
            UserReview.review_date >= cutoff,
        )
        .first()
    )
    if sent_row and sent_row.cnt and sent_row.cnt >= 3:
        sent_scores_rows = (
            db.query(UserReview.sentiment_score)
            .filter(
                UserReview.competitor_id == comp_id,
                UserReview.review_date >= cutoff,
            )
            .all()
        )
        scores = [r[0] for r in sent_scores_rows]
        mean_s = sum(scores) / len(scores)
        std_s = math.sqrt(sum((s - mean_s) ** 2 for s in scores) / len(scores))
        sent_consistency = max(0, min(1, 1 - std_s))
    else:
        sent_consistency = 0.5
        std_s = 0

    score = round(price_stability * 50 + sent_consistency * 50)
    evidence = f"价格变异系数 {cv:.2f}，情感标准差 {std_s:.2f}"
    return score, evidence


def _score_innovation(comp_id: int, db: Session) -> tuple:
    """创新力评分 — 功能增长 + 关键词新颖度"""
    # 功能数量增长（total feature_updates）
    feat_count = (
        db.query(func.count(Change.id))
        .filter(
            Change.competitor_id == comp_id,
            Change.change_type.in_(['feature_update', 'version_change']),
        )
        .scalar()
    ) or 0
    feat_score = min(feat_count / 20, 1.0)

    # 从评论中提取创新相关关键词密度
    review_rows = (
        db.query(UserReview.content)
        .filter(UserReview.competitor_id == comp_id)
        .all()
    )
    innovation_kw = {"ai", "新功能", "更新", "升级", "优化", "大模型", "智能", "自动化", "新版", "发布", "推出"}
    if review_rows:
        all_text = "".join([r[0] for r in review_rows if r[0]])
        total_chars = max(len(all_text), 1)
        kw_hits = sum(all_text.count(kw) for kw in innovation_kw)
        kw_density = min(kw_hits / (total_chars / 50), 1.0)  # 每50字命中一次 = 满分
    else:
        kw_density = 0.3

    score = round(feat_score * 50 + kw_density * 50)
    evidence = f"功能变更{feat_count}次，创新关键词命中率 {(kw_density * 100):.0f}%"
    return score, evidence


def _score_sentiment(comp_id: int, db: Session) -> tuple:
    """客户口碑评分 — 情感趋势 + 评论量增长"""
    cutoff_recent = datetime.utcnow() - timedelta(days=30)
    cutoff_prev = datetime.utcnow() - timedelta(days=60)

    # 近30天情感均值
    sent_row = (
        db.query(
            func.avg(UserReview.sentiment_score).label("avg_s"),
            func.count(UserReview.id).label("cnt"),
        )
        .filter(
            UserReview.competitor_id == comp_id,
            UserReview.review_date >= cutoff_recent,
        )
        .first()
    )
    avg_sent = sent_row.avg_s if sent_row and sent_row.avg_s is not None else 0
    recent_cnt = sent_row.cnt if sent_row else 1
    sent_score = (avg_sent + 1) / 2  # 映射 [-1,1] → [0,1]

    # 评论量增长率（对比前30天）
    prev_cnt = (
        db.query(func.count(UserReview.id))
        .filter(
            UserReview.competitor_id == comp_id,
            UserReview.review_date >= cutoff_prev,
            UserReview.review_date < cutoff_recent,
        )
        .scalar()
    ) or 1
    growth_ratio = (recent_cnt - prev_cnt) / max(prev_cnt, 1)
    growth_score = max(0, min(1, growth_ratio + 0.5))  # 0增长 → 0.5分

    score = round(sent_score * 60 + growth_score * 40)
    evidence = (
        f"情感均值 {avg_sent:.2f}，评论量 {recent_cnt} 条"
        f"（环比 {'+' if growth_ratio > 0 else ''}{growth_ratio * 100:.0f}%）"
    )
    return score, evidence


def _score_threat(aggressiveness: float, innovation: float, stability: float,
                  market_share: float, max_share: float) -> tuple:
    """威胁等级 — 加权综合评分"""
    share_norm = min(market_share / max(max_share, 1), 1.0) if max_share > 0 else 0.2
    score = round(
        aggressiveness * 0.25 +
        innovation * 0.25 +
        share_norm * 100 * 0.25 +
        (100 - stability) * 0.25
    )
    evidence = (
        f"攻击{aggressiveness} + 创新{innovation} "
        f"+ 份额{share_norm * 100:.0f} + 波动{(100 - stability)} "
        f"→ 综合威胁{score}"
    )
    return score, evidence


def _compute_impl(db: Session) -> List[Dict[str, Any]]:
    """计算所有竞品的5维态势评分（ORC实现核心）"""
    comp_rows = db.query(Competitor).order_by(Competitor.id).all()

    max_share = max((c.market_share or 0 for c in comp_rows), default=1)

    result = []
    for c in comp_rows:
        comp_id = c.id
        name = c.name
        share = c.market_share or 0

        agg_score, agg_ev = _score_aggressiveness(comp_id, db)
        stab_score, stab_ev = _score_stability(comp_id, db)
        inno_score, inno_ev = _score_innovation(comp_id, db)
        sent_score, sent_ev = _score_sentiment(comp_id, db)

        threat_score, threat_ev = _score_threat(
            agg_score, inno_score, stab_score, share, max_share
        )

        result.append({
            "competitor_id": comp_id,
            "name": name,
            "market_share": share,
            "scores": {
                "aggressiveness": {"value": agg_score, "evidence": agg_ev},
                "stability":       {"value": stab_score, "evidence": stab_ev},
                "innovation":      {"value": inno_score, "evidence": inno_ev},
                "sentiment":       {"value": sent_score, "evidence": sent_ev},
                "threat":          {"value": threat_score, "evidence": threat_ev},
            },
            "computed_at": datetime.now().isoformat(),
        })

    # 按威胁等级排序
    result.sort(key=lambda x: x["scores"]["threat"]["value"], reverse=True)
    return result


def compute_posture_scores(db: Session = None) -> List[Dict[str, Any]]:
    """计算所有竞品的5维态势评分（公共接口，保持向后兼容）"""
    if db is not None:
        return _compute_impl(db)

    from app.core.database import SessionLocal
    session = SessionLocal()
    try:
        result = _compute_impl(session)
        session.commit()
        return result
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
