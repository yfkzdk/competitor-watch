"""
采集管理API路由
"""
from fastapi import APIRouter, HTTPException, Query
from app.models.common import SuccessResponse
from app.services.scraper_service import scraper_service
from app.services.change_detection_service import change_detection_service
from app.services.alert_service import alert_service
from app.core.executor import run_sync_function
from typing import Optional
import json

router = APIRouter()


# ========== 采集规则配置 ==========

@router.get("/scraper/configs", response_model=SuccessResponse)
async def get_scraper_configs(
    competitor_id: Optional[int] = Query(None),
    enabled_only: bool = Query(False)
):
    """获取采集规则列表"""
    configs = await run_sync_function(
        scraper_service.get_configs, competitor_id, enabled_only
    )
    # 解析JSON字段
    for c in configs:
        if c.get('selectors'):
            try:
                c['selectors'] = json.loads(c['selectors'])
            except (json.JSONDecodeError, TypeError):
                pass
        if c.get('headers'):
            try:
                c['headers'] = json.loads(c['headers'])
            except (json.JSONDecodeError, TypeError):
                pass
    return SuccessResponse(data=configs)


@router.post("/scraper/configs", response_model=SuccessResponse)
async def create_scraper_config(
    competitor_id: int = Query(...),
    name: str = Query(...),
    target_url: str = Query(...),
    scrape_type: str = Query('playwright'),
    selectors: str = Query('{}', description="JSON格式选择器"),
    headers: str = Query('{}', description="JSON格式请求头"),
    wait_selector: str = Query(None),
    wait_timeout: int = Query(10000),
    use_stealth: bool = Query(True),
    frequency_minutes: int = Query(60)
):
    """创建采集规则"""
    try:
        sel_dict = json.loads(selectors) if isinstance(selectors, str) else {}
        hdr_dict = json.loads(headers) if isinstance(headers, str) else {}
    except json.JSONDecodeError:
        raise HTTPException(status_code=422, detail="selectors/headers 必须是合法JSON")

    config_id = await run_sync_function(
        scraper_service.create_config,
        competitor_id, name, target_url, scrape_type,
        sel_dict, hdr_dict, wait_selector, wait_timeout,
        use_stealth, frequency_minutes
    )
    return SuccessResponse(data={"config_id": config_id})


@router.put("/scraper/configs/{config_id}", response_model=SuccessResponse)
async def update_scraper_config(config_id: int, **kwargs):
    """更新采集规则"""
    success = await run_sync_function(scraper_service.update_config, config_id, **kwargs)
    return SuccessResponse(data={"updated": success})


@router.delete("/scraper/configs/{config_id}", response_model=SuccessResponse)
async def delete_scraper_config(config_id: int):
    """删除采集规则"""
    await run_sync_function(scraper_service.delete_config, config_id)
    return SuccessResponse(data={"deleted": True})


# ========== 采集执行 ==========

@router.post("/scraper/fetch/{config_id}", response_model=SuccessResponse)
async def fetch_by_config(config_id: int):
    """根据配置执行采集"""
    result = await scraper_service.fetch_and_extract(config_id)
    return SuccessResponse(data=result)


@router.post("/scraper/fetch", response_model=SuccessResponse)
async def fetch_by_competitor(competitor_id: int = Query(...)):
    """执行竞品的所有采集任务"""
    configs = await run_sync_function(scraper_service.get_configs, competitor_id, True)
    if not configs:
        raise HTTPException(status_code=404, detail="该竞品无启用的采集规则")

    results = []
    for config in configs:
        result = await scraper_service.fetch_and_extract(config['id'])
        results.append(result)

        # 数据闭环：采集→变化检测→告警
        if result.get('status') == 'success' and result.get('extracted_data'):
            await _trigger_change_detection(competitor_id, result)

    return SuccessResponse(data=results)


@router.post("/scraper/fetch-all", response_model=SuccessResponse)
async def fetch_all():
    """执行所有启用的采集任务"""
    results = await scraper_service.run_all_enabled()

    # 数据闭环
    for result in results:
        if result.get('status') == 'success' and result.get('extracted_data'):
            await _trigger_change_detection(result['competitor_id'], result)

    return SuccessResponse(data=results)


# ========== 采集结果 ==========

@router.get("/scraper/results", response_model=SuccessResponse)
async def get_scrape_results(
    competitor_id: Optional[int] = Query(None),
    config_id: Optional[int] = Query(None),
    limit: int = Query(20)
):
    """获取采集结果历史"""
    results = await run_sync_function(
        scraper_service.get_results, competitor_id, config_id, limit
    )
    # 解析JSON字段
    for r in results:
        if r.get('extracted_data'):
            try:
                r['extracted_data'] = json.loads(r['extracted_data'])
            except (json.JSONDecodeError, TypeError):
                pass
    return SuccessResponse(data=results)


@router.get("/scraper/results/latest/{competitor_id}", response_model=SuccessResponse)
async def get_latest_result(competitor_id: int):
    """获取竞品最新采集结果"""
    result = await run_sync_function(scraper_service.get_latest_result, competitor_id)
    if not result:
        return SuccessResponse(data={"message": "暂无采集数据"})
    if result.get('extracted_data'):
        try:
            result['extracted_data'] = json.loads(result['extracted_data'])
        except (json.JSONDecodeError, TypeError):
            pass
    return SuccessResponse(data=result)


# ========== 数据闭环辅助 ==========

async def _trigger_change_detection(competitor_id: int, scrape_result: dict):
    """采集后自动触发变化检测和告警"""
    extracted = scrape_result.get('extracted_data', {})
    price = scrape_result.get('price')
    in_stock = scrape_result.get('in_stock')

    try:
        # 价格变化检测
        if price is not None:
            changes = await run_sync_function(
                change_detection_service.compare_snapshots,
                competitor_id, 'price', {'price': price}
            )
            if changes:
                await _auto_create_alert(competitor_id, changes)

        # 库存变化检测
        if in_stock is not None:
            stock_val = True if in_stock == 'true' or in_stock is True else False
            changes = await run_sync_function(
                change_detection_service.compare_snapshots,
                competitor_id, 'stock', {'in_stock': stock_val}
            )
            if changes:
                await _auto_create_alert(competitor_id, changes)

    except Exception as e:
        import logging
        logging.error(f"变化检测失败: {e}")


async def _auto_create_alert(competitor_id: int, changes: dict):
    """自动创建告警（通过alert_service，支持去重）"""
    if changes['type'] == 'price_change':
        msg = f"价格从{changes['old_price']}变为{changes['new_price']} ({changes['change_percentage']:.1f}%)"
    elif changes['type'] == 'sentiment_change':
        msg = f"情感分布变化: 正面{changes['old_sentiment']['positive']}→{changes['new_sentiment']['positive']}"
    elif changes['type'] == 'stock_change':
        msg = f"库存状态变化: {'有货' if changes['new_stock'] else '缺货'}"
    else:
        msg = f"检测到{changes['type']}变化"

    try:
        alert_id = await run_sync_function(
            alert_service.trigger_alert,
            competitor_id, changes['type'], changes['severity'], msg, changes
        )
        if alert_id:
            changes['alert_id'] = alert_id
    except Exception as e:
        import logging
        logging.error(f"自动告警失败: {e}")
