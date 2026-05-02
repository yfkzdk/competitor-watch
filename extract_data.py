"""Extract all API data for offline demo"""
import json, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from app.core.database import db_manager
from app.routers.alerts import _get_alerts, _get_alert_stats, _get_alert_rules
from app.routers.competitors import _get_matrix_data
from app.services.posture_scorer import compute_posture_scores

def to_json(obj):
    return json.loads(json.dumps(obj, ensure_ascii=False, default=str))

data = {}

# Dashboard stats
rows = db_manager.execute_query("SELECT COUNT(*) as c FROM competitors")
data["/api/dashboard/stats"] = {
    "success": True,
    "data": {
        "competitorsTotal": rows[0]["c"],
        "activeCompetitors": db_manager.execute_query("SELECT COUNT(*) as c FROM competitors WHERE status='active'")[0]["c"],
        "priceRecords": db_manager.execute_query("SELECT COUNT(*) as c FROM price_history")[0]["c"],
        "reviewRecords": db_manager.execute_query("SELECT COUNT(*) as c FROM user_reviews")[0]["c"],
        "changesDetected": db_manager.execute_query("SELECT COUNT(*) as c FROM changes")[0]["c"],
        "alertsPending": db_manager.execute_query("SELECT COUNT(*) as c FROM alert_history WHERE is_read=0")[0]["c"],
    }
}
print("Dashboard stats ✓")

# Competitors
comps = db_manager.execute_query("SELECT * FROM competitors")
competitors = []
for c in comps:
    d = dict(c)
    d["metrics"] = {
        "market_share": d.get("market_share", 0),
        "price_index": d.get("price_index", 0),
        "user_rating": d.get("user_rating", 0),
        "growth": d.get("growth", 0),
        "feature_count": d.get("feature_count", 0),
        "innovation_velocity": d.get("innovation_velocity", 0),
        "security_mentions": d.get("security_mentions", 0),
    }
    competitors.append(d)
data["/api/competitors"] = {"success": True, "data": competitors}
print("Competitors ✓")

# Matrix
matrix = to_json(_get_matrix_data())
data["/api/competitors/matrix"] = {"success": True, "data": matrix}
print("Matrix ✓")

# Posture
scores = to_json(compute_posture_scores())
data["/api/competitors/posture"] = {"success": True, "data": scores}
print("Posture ✓")

# Changes
changes = db_manager.execute_query(
    """SELECT ch.*, c.name as competitor_name FROM changes ch
       JOIN competitors c ON ch.competitor_id = c.id
       ORDER BY ch.detected_at DESC LIMIT 50"""
)
data["/api/diff/changes?limit=50"] = {"success": True, "data": [dict(r) for r in changes]}
data["/api/diff/changes?limit=20"] = {"success": True, "data": [dict(r) for r in changes[:20]]}
data["/api/diff/changes?limit=10"] = {"success": True, "data": [dict(r) for r in changes[:10]]}
print("Changes ✓")

# Alerts
alerts_data = to_json(_get_alerts(limit=50))
data["/api/alerts?limit=50"] = {"success": True, "data": alerts_data}
stats_data = to_json(_get_alert_stats())
data["/api/alerts/stats"] = {"success": True, "data": stats_data}
rules_data = to_json(_get_alert_rules())
data["/api/alerts/rules"] = {"success": True, "data": rules_data}
print("Alerts ✓")

# Sentiment for each competitor
for comp in competitors:
    cid = comp["id"]
    dist = db_manager.execute_query(
        """SELECT
            SUM(CASE WHEN sentiment_score > 0.2 THEN 1 ELSE 0 END) as positive,
            SUM(CASE WHEN sentiment_score BETWEEN -0.2 AND 0.2 THEN 1 ELSE 0 END) as neutral,
            SUM(CASE WHEN sentiment_score < -0.2 THEN 1 ELSE 0 END) as negative,
            COUNT(*) as total, AVG(sentiment_score) as avg_score
        FROM user_reviews WHERE competitor_id = ?""", (cid,))
    d = dist[0] if dist else {}
    data[f"/api/v1/reviews/sentiment?competitor_id={cid}&days=90"] = {
        "success": True,
        "data": {
            "competitor_id": cid,
            "total_reviews": d.get("total", 0) or 0,
            "average_sentiment_score": d.get("avg_score", 0) or 0,
            "sentiment_distribution": {
                "positive": d.get("positive", 0) or 0,
                "neutral": d.get("neutral", 0) or 0,
                "negative": d.get("negative", 0) or 0,
            }
        }
    }
print("Sentiment data ✓")

# Sentiment trend for each competitor
from datetime import datetime, timedelta
for comp in competitors:
    cid = comp["id"]
    rows = db_manager.execute_query(
        """SELECT DATE(review_date) as day, AVG(sentiment_score) as avg_sentiment, COUNT(*) as review_count
           FROM user_reviews WHERE competitor_id = ? AND review_date >= DATE('now', '-90 days')
           GROUP BY DATE(review_date) ORDER BY day""", (cid,))
    data[f"/api/reviews/sentiment-trend?competitor_id={cid}&days=90"] = {
        "success": True, "data": [dict(r) for r in rows]
    }
print("Sentiment trends ✓")

# Price history for each competitor (limited to 200)
for comp in competitors:
    cid = comp["id"]
    rows = db_manager.execute_query(
        "SELECT * FROM price_history WHERE competitor_id=? ORDER BY recorded_at DESC LIMIT 200", (cid,))
    data[f"/api/v1/prices/history?competitor_id={cid}&limit=200"] = {
        "success": True, "data": [dict(r) for r in rows]
    }
print("Price history ✓")

# Reviews for each competitor (limited to 100)
for comp in competitors:
    cid = comp["id"]
    rows = db_manager.execute_query(
        "SELECT * FROM user_reviews WHERE competitor_id=? ORDER BY review_date DESC LIMIT 100", (cid,))
    data[f"/api/v1/reviews?competitor_id={cid}&limit=100"] = {
        "success": True, "data": [dict(r) for r in rows]
    }
print("Reviews ✓")

# Keywords for each competitor
for comp in competitors:
    cid = comp["id"]
    try:
        from app.routers.system import _get_product_keywords
        kw = to_json(_get_product_keywords(cid))
        data[f"/api/product/{cid}/keywords"] = {"success": True, "data": kw}
    except Exception as e:
        data[f"/api/product/{cid}/keywords"] = {"success": True, "data": []}
print("Keywords ✓")

outpath = os.path.join(os.path.dirname(__file__), "offline_data.json")
with open(outpath, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False)
print(f"\nSaved {len(data)} endpoints to {outpath}")
print(f"File size: {os.path.getsize(outpath)/1024:.0f} KB")
