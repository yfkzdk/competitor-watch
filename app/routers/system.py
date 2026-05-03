"""
系统状态、报告、产品关键词与分类路由

从 Flask web_server.py 迁移的核心路由:
  - GET /api/status              系统状态检查
  - GET /api/business-report/{competitor_name}  商业洞察报告
  - GET /api/reports             历史报告列表
  - GET /api/product/{comp_id}/keywords  产品功能关键词
  - GET /api/product/categories  产品分类统计
"""
import json
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import func, text

from app.core.database import SessionLocal
from app.core.models import Competitor, MonitoringLog, AnalysisReport, UserReview, Change
from app.core.executor import run_sync_function
from app.models.common import SuccessResponse

logger = logging.getLogger(__name__)
router = APIRouter()


# ── 同步业务函数 ─────────────────────────────────────────────────

def _get_system_status() -> Dict[str, Any]:
    """系统状态（同步）"""
    db_available = True
    try:
        db = SessionLocal()
        try:
            db.execute(text("SELECT 1"))
        finally:
            db.close()
    except Exception:
        db_available = False

    report_available = False
    fetcher_available = False

    return {
        "system_time": datetime.now().isoformat(),
        "db_available": db_available,
        "report_available": report_available,
        "fetcher_available": fetcher_available,
    }


def _generate_business_report(competitor_name: str) -> Dict[str, Any]:
    """商业洞察报告（同步），返回报告数据或抛出异常"""
    db = SessionLocal()
    try:
        # 查找竞品
        comp = db.query(Competitor).filter(Competitor.name == competitor_name).first()
        if not comp:
            raise HTTPException(
                status_code=404,
                detail={
                    "success": False,
                    "error": f"竞品 {competitor_name} 不存在于数据库中",
                    "status": "INSUFFICIENT",
                    "estimated_retry_minutes": 5,
                },
            )

        # 获取监控日志
        cutoff = datetime.utcnow() - timedelta(hours=720)
        logs = db.query(MonitoringLog).filter(
            MonitoringLog.competitor_id == comp.id,
            MonitoringLog.checked_at >= cutoff,
        ).order_by(MonitoringLog.checked_at.desc()).all()

        if not logs:
            raise HTTPException(
                status_code=202,
                detail={
                    "success": False,
                    "error": "数据采集与清洗中，暂无足够数据生成报告",
                    "status": "INSUFFICIENT",
                    "estimated_retry_minutes": 30,
                    "hint": "请先触发数据采集（POST /api/competitors/<id>/fetch）",
                },
            )

        # Generate trend data from monitoring logs
        trend_data = {
            "trend_metrics": {},
            "period_analyzed": f"{len(logs)} monitoring logs",
            "analysis_method": "statistical",
        }

        # Profile data from competitor metrics
        m = trend_data.setdefault("trend_metrics", {})
        m["innovation_velocity"] = (comp.growth or 0) / 2 + (comp.user_rating or 4) * 0.5
        m["stability_index"] = (comp.price_index or 90) / 12
        m["security_focus"] = 5 + (comp.price_index or 90) * 0.02
        m["market_alignment"] = (comp.market_share or 0) * 1.5 + (comp.user_rating or 4)
        m["tech_debt_risk"] = max(0, 10 - m.get("stability_index", 5) / 2)

        # Build report from computed metrics
        report_data = {
            "competitor_name": competitor_name,
            "generated_at": datetime.now().isoformat(),
            "executive_summary": {
                "situation": f"{competitor_name} 当前市场占有率 {comp.market_share or 0}%，"
                             f"增长率 {comp.growth or 0}%，用户评分 {comp.user_rating or 0}。",
                "implication": f"价格指数 {comp.price_index or 0}，创新速度 {m['innovation_velocity']:.1f}。",
            },
            "opportunities": [
                {"title": "市场扩展", "insight": f"当前增速 {comp.growth or 0}%，建议关注高增长细分市场。"},
            ],
            "risks": [
                {"title": "竞争压力", "severity": "medium", "insight": "头部竞品可能采取激进定价策略。"},
            ],
            "recommendations": [
                "持续监控价格变化，及时调整策略",
                "关注竞品功能更新与技术动向",
            ],
            "confidence": {"score": 0.75, "factors": ["data_completeness", "recency"]},
            "monitoring_summary": f"近30天 {len(logs)} 条监控日志，报告基于统计模型生成。",
        }

        # 保存报告（使用独立 session，与查询 session 分离）
        try:
            _save_report(comp.id, "insight", report_data)
        except Exception:
            logger.warning("保存报告到数据库失败，但报告已生成", exc_info=True)

        return report_data
    finally:
        db.close()


def _save_report(competitor_id: int, report_type: str, report_data: Dict) -> None:
    """保存分析报告（同步），使用 SQLAlchemy ORM"""
    # 提取 executive_summary
    exec_summary = report_data.get("executive_summary", {})
    if isinstance(exec_summary, dict):
        insight_str = f"{exec_summary.get('situation', '')} {exec_summary.get('implication', '')}"
    else:
        insight_str = str(exec_summary)

    # 提取 evidence
    opportunities = report_data.get("opportunities", [])
    risks = report_data.get("risks", [])
    evidence = []
    for opp in opportunities:
        evidence.append({"type": "opportunity", "title": opp.get("title", ""), "insight": opp.get("insight", "")})
    for risk in risks:
        evidence.append({"type": "risk", "title": risk.get("title", ""), "severity": risk.get("severity", "")})

    # 提取 confidence
    confidence_data = report_data.get("confidence", {})
    if isinstance(confidence_data, dict):
        confidence = confidence_data.get("score", 0.8)
    elif isinstance(confidence_data, (int, float)):
        confidence = confidence_data
    else:
        confidence = 0.8

    # 提取 recommendations
    action_plan = report_data.get("action_plan", {})
    recommendations = []
    for action in action_plan.get("immediate", []):
        recommendations.append({"priority": "immediate", "action": action})
    for action in action_plan.get("short_term", []):
        recommendations.append({"priority": "short_term", "action": action})
    for action in action_plan.get("medium_term", []):
        recommendations.append({"priority": "medium_term", "action": action})

    model_name = f"{report_type}_model"

    db = SessionLocal()
    try:
        report = AnalysisReport(
            competitor_id=competitor_id,
            report_type=report_type,
            summary=insight_str,
            content=evidence,
            confidence_score=confidence,
            recommendations=recommendations,
            model_used=model_name,
        )
        db.add(report)
        db.flush()
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def _get_reports(competitor_id: Optional[int], limit: int) -> List[Dict]:
    """获取历史报告列表（同步）"""
    db = SessionLocal()
    try:
        q = db.query(AnalysisReport)
        if competitor_id:
            q = q.filter(AnalysisReport.competitor_id == competitor_id)
        rows = q.order_by(AnalysisReport.created_at.desc()).limit(limit).all()
        return [{
            "id": r.id,
            "competitor_id": r.competitor_id,
            "report_type": r.report_type,
            "title": r.title,
            "summary": r.summary,
            "content": r.content,
            "confidence_score": r.confidence_score,
            "recommendations": r.recommendations,
            "model_used": r.model_used,
            "created_at": r.created_at,
        } for r in rows]
    finally:
        db.close()


def _get_product_keywords(comp_id: int) -> Dict[str, Any]:
    """从真实评论数据提取产品功能关键词（使用 jieba TF-IDF）"""
    db = SessionLocal()
    try:
        comp = db.query(Competitor).filter(Competitor.id == comp_id).first()
        if not comp:
            raise HTTPException(status_code=404, detail="产品不存在")

        # 从真实评论内容提取关键词
        review_rows = db.query(UserReview.content).filter(
            UserReview.competitor_id == comp_id
        ).all()

        if review_rows:
            try:
                import jieba.analyse

                all_text = " ".join([r.content for r in review_rows if r.content])
                if all_text.strip():
                    tfidf = jieba.analyse.extract_tags(all_text, topK=20, withWeight=True)
                    keywords = [{"word": w, "count": round(c * 100)} for w, c in tfidf if len(w) >= 2]
                    if keywords:
                        return {"keywords": keywords, "product": comp.name, "source": "review_tfidf"}
            except Exception:
                logger.warning("jieba 关键词提取失败，降级为属性关键词", exc_info=True)

        # 降级：基于产品属性生成关键词
        base_keywords = [
            {"word": "价格监控", "count": (comp.price_index or 90) / 10},
            {"word": "用户增长", "count": (comp.growth or 0) / 2 + 5},
            {"word": "市场份额", "count": (comp.market_share or 0) / 5 + 3},
            {"word": "产品功能", "count": (comp.feature_count or 0) / 5 + 2},
            {"word": "用户评分", "count": (comp.user_rating or 4) * 3},
            {"word": "创新速度", "count": (comp.innovation_velocity or 0) / 2 + 4},
            {"word": "安全特性", "count": (comp.security_mentions or 0) + 3},
            {"word": "市场定位", "count": 8},
            {"word": "竞争分析", "count": 10},
            {"word": "趋势预测", "count": 7},
            "数据分析", "实时监控", "智能预警", "自动化", "API集成",
            "报告生成", "多平台", "定制化", "可视化", "数据采集",
        ]
        keywords_list = []
        for kw in base_keywords:
            if isinstance(kw, str):
                keywords_list.append({"word": kw, "count": 5 + int(10 * (hash(kw) % 100) / 100)})
            else:
                keywords_list.append(kw)
        keywords = sorted(keywords_list, key=lambda x: x["count"], reverse=True)
        return {"keywords": keywords, "product": comp.name, "source": "attribute_fallback"}
    finally:
        db.close()


def _get_product_categories() -> List[Dict[str, Any]]:
    """获取产品分类统计（同步）"""
    db = SessionLocal()
    try:
        # 尝试从 product_categories 表获取（该表无 ORM 模型，使用 raw text 查询）
        try:
            table_check = db.execute(
                text("SELECT name FROM sqlite_master WHERE type='table' AND name='product_categories'")
            ).fetchall()
            if table_check:
                rows = db.execute(text(
                    """SELECT category_level1 as category, COUNT(*) as count
                       FROM product_categories
                       WHERE is_active = 1
                       GROUP BY category_level1
                       ORDER BY count DESC"""
                )).fetchall()
                return [{"category": r[0], "count": r[1]} for r in rows]
        except Exception:
            pass

        # 降级：从竞品表的 type 字段聚合
        try:
            rows = db.query(
                Competitor.type.label("category"),
                func.count(Competitor.id).label("count"),
            ).filter(
                Competitor.type.isnot(None),
                Competitor.type != "",
            ).group_by(Competitor.type).order_by(func.count(Competitor.id).desc()).all()
            if rows:
                return [{"category": r.category, "count": r.count} for r in rows]
        except Exception:
            pass

        # 最终降级：返回空列表
        return []
    finally:
        db.close()


def _get_sentiment_trend(competitor_id: int, days: int = 30) -> List[Dict[str, Any]]:
    """获取情感趋势数据（按天聚合）"""
    db = SessionLocal()
    try:
        cutoff = datetime.utcnow() - timedelta(days=days)
        rows = db.query(
            func.date(UserReview.review_date).label("day"),
            func.avg(UserReview.sentiment_score).label("avg_sentiment"),
            func.count(UserReview.id).label("review_count"),
        ).filter(
            UserReview.competitor_id == competitor_id,
            UserReview.review_date >= cutoff,
        ).group_by(func.date(UserReview.review_date)).order_by("day").all()

        return [{"day": r.day, "avg_sentiment": r.avg_sentiment, "review_count": r.review_count} for r in rows]
    finally:
        db.close()


def _get_enhanced_report() -> Dict[str, Any]:
    """生成规则引擎增强的分析报告，降级返回基础分析"""
    db = SessionLocal()
    try:
        # 获取所有竞品
        comps = db.query(Competitor).all()
        competitors = [{
            "id": c.id, "name": c.name, "url": c.url, "category": c.category,
            "status": c.status, "priority": c.priority, "description": c.description,
            "type": c.type, "frequency": c.frequency,
            "market_share": c.market_share, "price_index": c.price_index,
            "user_rating": c.user_rating, "growth": c.growth,
            "feature_count": c.feature_count, "innovation_velocity": c.innovation_velocity,
            "security_mentions": c.security_mentions,
            "last_checked": c.last_checked, "created_at": c.created_at, "updated_at": c.updated_at,
        } for c in comps]

        # 获取近期变更
        change_rows = db.query(Change).order_by(Change.detected_at.desc()).limit(20).all()
        changes = [{
            "id": ch.id, "competitor_id": ch.competitor_id,
            "field_name": ch.field_name, "old_value": ch.old_value, "new_value": ch.new_value,
            "change_type": ch.change_type, "severity": ch.severity,
            "detected_at": ch.detected_at, "is_read": ch.is_read,
        } for ch in change_rows]

        report = {
            "competitors": competitors,
            "changes": changes,
            "generated_at": datetime.now().isoformat(),
            "analysis_used": False,
        }

        # 规则引擎分析
        try:
            from app.services.analysis_engine import is_available, generate_competitor_insight

            if is_available():
                insights = []
                for comp in comps[:5]:
                    metric_data = {
                        "market_share": comp.market_share or 0,
                        "price_index": comp.price_index or 90,
                        "user_rating": comp.user_rating or 4,
                        "growth": comp.growth or 0,
                        "innovation_velocity": comp.innovation_velocity or 0,
                    }
                    insight = generate_competitor_insight(comp.name, metric_data)
                    if insight:
                        insights.append({
                            "competitor": comp.name,
                            "insight": insight.get("insight", ""),
                            "evidence": insight.get("evidence", []),
                            "confidence": insight.get("confidence", 0.7),
                            "recommendations": insight.get("recommendations", []),
                        })
                if insights:
                    report["insights"] = insights
                    report["analysis_used"] = True
        except Exception:
            logger.warning("规则引擎分析增强失败", exc_info=True)

        # 构建基础分析指标
        total_share = sum(c.market_share or 0 for c in comps)
        avg_price = sum(c.price_index or 90 for c in comps) / max(len(comps), 1)
        avg_rating = sum(c.user_rating or 0 for c in comps) / max(len(comps), 1)
        avg_growth = sum(c.growth or 0 for c in comps) / max(len(comps), 1)

        report["aggregates"] = {
            "total_market_share": round(total_share, 1),
            "avg_price_index": round(avg_price, 0),
            "avg_user_rating": round(avg_rating, 1),
            "avg_growth": round(avg_growth, 1),
            "competitor_count": len(comps),
        }

        return report
    finally:
        db.close()


# ── API 端点 ─────────────────────────────────────────────────────


@router.get("/status", response_model=SuccessResponse)
async def api_status():
    """系统状态检查"""
    data = await run_sync_function(_get_system_status)
    return SuccessResponse(data=data)


@router.get("/business-report/{competitor_name}")
async def api_business_report(competitor_name: str):
    """生成商业洞察报告"""
    try:
        data = await run_sync_function(_generate_business_report, competitor_name)
        return {"success": True, "data": data}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"关键词提取失败 (competitor_id={comp_id}): {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "success": False,
                "error": f"报告生成失败: {e}",
                "status": "ERROR",
            },
        )


@router.get("/reports", response_model=SuccessResponse)
async def api_get_reports(
    competitor_id: Optional[int] = Query(None, description="竞品ID过滤"),
    limit: int = Query(10, ge=1, le=100, description="返回条数"),
):
    """获取历史报告列表"""
    data = await run_sync_function(_get_reports, competitor_id, limit)
    return SuccessResponse(data=data)


@router.get("/product/{comp_id}/keywords", response_model=SuccessResponse)
async def api_product_keywords(comp_id: int):
    """获取产品功能关键词"""
    data = await run_sync_function(_get_product_keywords, comp_id)
    return SuccessResponse(data=data)


@router.get("/product/categories", response_model=SuccessResponse)
async def api_product_categories():
    """获取产品分类统计"""
    data = await run_sync_function(_get_product_categories)
    return SuccessResponse(data=data)


@router.get("/reviews/sentiment-trend")
async def api_sentiment_trend(
    competitor_id: int = Query(..., description="竞品ID"),
    days: int = Query(30, ge=7, le=90, description="统计天数"),
):
    """获取评论情感趋势（按天聚合）"""
    data = await run_sync_function(_get_sentiment_trend, competitor_id, days)
    return {"success": True, "data": data}


@router.get("/report/enhanced")
async def api_enhanced_report():
    """规则引擎增强的分析报告"""
    data = await run_sync_function(_get_enhanced_report)
    return {"success": True, "data": data}
