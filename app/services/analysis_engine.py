"""
Analysis Engine — deterministic rule-based competitive analysis.

Evaluates competitor positioning across growth, pricing, user satisfaction,
and innovation velocity dimensions. All outputs are computed from input metrics;
no randomness, no external API dependency.
"""
import hashlib
import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

CHANGE_TEMPLATES = {
    "price_change": [
        "价格下调{delta}%，可能意在扩大市场份额",
        "价格上调{delta}%，或反映成本传导策略",
        "新增{product_desc}定价方案，丰富产品矩阵",
    ],
    "feature_update": [
        "上线{product_desc}功能，技术迭代信号明显",
        "优化{product_desc}体验，用户留存策略加码",
    ],
    "marketing_campaign": [
        "推出{product_desc}营销活动，品牌声量上升",
    ],
    "new_product": [
        "发布全新产品{product_desc}，进入新赛道",
    ],
    "default": [
        "在{change_type}方面有{product_desc}变动，需持续关注",
    ],
}

INSIGHT_TEMPLATES = {
    "aggressive": [
        "市场进攻态势明显，建议加强差异化应对",
        "价格战策略激进，需关注利润空间变化",
    ],
    "rising": [
        "成长势头强劲，创新能力驱动增长",
        "用户口碑上升，产品竞争力持续增强",
    ],
    "stable": [
        "表现平稳，经营节奏趋于成熟",
        "核心指标波动不大，市场地位稳固",
    ],
    "defensive": [
        "以守为攻，维护现有份额的策略较为稳健",
        "用户留存导向，产品体验持续优化中",
    ],
    "declining": [
        "增长放缓，可能需要战略性调整",
        "用户关注度下降，警惕市场份额流失",
    ],
}


def _stable_pick(pool: list, seed: str) -> str:
    """Deterministic selection based on content hash, not random."""
    h = int(hashlib.md5(seed.encode()).hexdigest()[:8], 16)
    return pool[h % len(pool)]


def _classify_competitor(metrics: Dict) -> str:
    growth = metrics.get("growth", 0)
    price_idx = metrics.get("price_index", 95)
    rating = metrics.get("user_rating", 4.0)
    innovation = metrics.get("innovation_velocity", 50)

    if growth > 10:
        return "rising"
    if price_idx < 80:
        return "aggressive"
    if rating >= 4.3 and innovation > 60:
        return "rising"
    if growth < -5:
        return "declining"
    if rating >= 4.0:
        return "stable"
    return "defensive"


def _build_evidence(metrics: Dict) -> List[str]:
    evidence = []
    growth = metrics.get("growth", 0)
    price_idx = metrics.get("price_index", 95)
    rating = metrics.get("user_rating", 4.0)
    innovation = metrics.get("innovation_velocity", 50)

    if growth > 5:
        evidence.append(f"近月增长率 +{growth}%，高于行业均值")
    elif growth < -3:
        evidence.append(f"近月增长率 {growth}%，低于行业均值")
    if price_idx < 85:
        evidence.append(f"价格指数 {price_idx}，处于低价竞争区间")
    elif price_idx > 110:
        evidence.append(f"价格指数 {price_idx}，溢价定位明显")
    if rating >= 4.3:
        evidence.append(f"用户评分 {rating}，口碑优势显著")
    elif rating < 3.5:
        evidence.append(f"用户评分 {rating}，满意度偏低")
    if innovation > 70:
        evidence.append(f"创新速度 {innovation}，技术迭代活跃")
    elif innovation < 30:
        evidence.append(f"创新速度 {innovation}，研发节奏偏慢")
    if not evidence:
        evidence.append("各维度指标均处于正常区间")
    return evidence


def _compute_confidence(evidence_count: int, metric_variance: float) -> float:
    """Confidence from evidence depth and metric consistency, not random."""
    base = min(0.85, 0.50 + evidence_count * 0.08)
    penalty = min(0.20, metric_variance * 0.01)
    return round(base - penalty, 2)


def _build_recommendations(category: str, metrics: Dict) -> List[str]:
    recs = {
        "aggressive": ["提升产品差异化功能，避免纯粹价格战", "监控对方利润空间变化，寻找定价节奏窗口"],
        "rising": ["研究其增长驱动因素，评估是否可借鉴", "在市场认知固化成势前，加大针对性投入"],
        "stable": ["寻找突破点打破平衡，避免陷入僵持", "检查其是否有潜在未暴露风险"],
        "defensive": ["继续加强用户体验，巩固现有客户关系", "关注其产品迭代方向，寻找差异化机会"],
        "declining": ["分析衰退原因，判断是否为争取转机窗口", "关注其客户流失方向，评估接盘可能"],
    }
    return recs.get(category, ["持续监控市场动态", "深入分析竞争态势"])


def summarize_change(competitor_name: str, change_type: str, change_data: Dict) -> Optional[str]:
    product_desc = (
        change_data.get("product_name")
        or change_data.get("feature_name")
        or change_data.get("description")
        or change_data.get("event_type")
        or change_data.get("category")
        or "产品"
    )
    delta = change_data.get("price_delta") or change_data.get("delta") or "0"
    partner = change_data.get("partner") or change_data.get("vendor") or "合作伙伴"

    pool = CHANGE_TEMPLATES.get(change_type, CHANGE_TEMPLATES["default"])
    template = _stable_pick(pool, f"{change_type}:{product_desc}:{delta}")
    summary = template.format(delta=delta, product_desc=product_desc, partner=partner, change_type=change_type)
    if len(summary) > 50:
        summary = summary[:47] + "..."
    logger.info(f"[AnalysisEngine] Summarized change for {competitor_name}: {summary}")
    return summary


def generate_competitor_insight(competitor_name: str, metrics: Dict) -> Optional[Dict]:
    category = _classify_competitor(metrics)
    pool = INSIGHT_TEMPLATES.get(category, INSIGHT_TEMPLATES["stable"])
    insight = _stable_pick(pool, f"{competitor_name}:{category}")
    evidence = _build_evidence(metrics)

    metric_values = [metrics.get(k, 0) for k in ("growth", "price_index", "user_rating", "innovation_velocity")]
    variance = max(metric_values) - min(metric_values)
    confidence = _compute_confidence(len(evidence), variance)

    recommendations = _build_recommendations(category, metrics)

    logger.info(f"[AnalysisEngine] Insight for {competitor_name}: category={category}, confidence={confidence}")
    return {
        "insight": insight,
        "evidence": evidence,
        "confidence": confidence,
        "recommendations": recommendations,
    }


def is_available() -> bool:
    return True
