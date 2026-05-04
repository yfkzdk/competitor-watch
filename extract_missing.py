"""Extract missing API endpoints"""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from app.core.database import db_manager

MISSING = {}

# Reports list
rows = db_manager.execute_query("SELECT * FROM analysis_reports ORDER BY created_at DESC LIMIT 10")
MISSING["/api/reports?limit=10"] = {"success": True, "data": [dict(r) for r in rows]}

for cid in [1,2,3,4,5]:
    rows = db_manager.execute_query(
        "SELECT * FROM analysis_reports WHERE competitor_id=? ORDER BY created_at DESC LIMIT 5", (cid,))
    MISSING[f"/api/reports?competitor_id={cid}&limit=5"] = {"success": True, "data": [dict(r) for r in rows]}

# Enhanced report - build from competitors directly
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

changes_raw = db_manager.execute_query(
    "SELECT ch.*, c.name as competitor_name FROM changes ch JOIN competitors c ON ch.competitor_id = c.id ORDER BY ch.detected_at DESC LIMIT 20")
changes = [dict(r) for r in changes_raw]

total_share = sum((c.get("market_share") or 0) for c in competitors)
avg_price = sum((c.get("price_index") or 0) for c in competitors) / max(len(competitors), 1)
avg_rating = sum((c.get("user_rating") or 0) for c in competitors) / max(len(competitors), 1)
avg_growth = sum((c.get("growth") or 0) for c in competitors) / max(len(competitors), 1)

MISSING["/api/report/enhanced"] = {
    "success": True,
    "data": {
        "competitors": competitors,
        "changes": changes,
        "generated_at": "2026-05-01T13:29:41",
        "analysis_used": False,
        "aggregates": {
            "total_market_share": round(total_share, 1),
            "avg_price_index": round(avg_price, 1),
            "avg_user_rating": round(avg_rating, 1),
            "avg_growth": round(avg_growth, 1),
            "competitor_count": len(competitors),
        }
    }
}

with open(os.path.join(os.path.dirname(__file__), "offline_data.json"), "r", encoding="utf-8") as f:
    existing = json.load(f)

existing.update(MISSING)

with open(os.path.join(os.path.dirname(__file__), "offline_data.json"), "w", encoding="utf-8") as f:
    json.dump(existing, f, ensure_ascii=False)

print(f"Added {len(MISSING)} endpoints. Total: {len(existing)}")
