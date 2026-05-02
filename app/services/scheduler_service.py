"""
任务调度服务 - 基于APScheduler + 智能动态调度
"""
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from typing import Dict, Optional
from datetime import datetime
from collections import deque
import asyncio
import logging

logger = logging.getLogger(__name__)


class SmartScheduler:
    """Adaptive monitoring frequency based on change rate and failure count.

    - High change rate → poll more often (cap at base_interval / 4)
    - Low change rate → back off (up to base_interval * 3)
    - Consecutive failures → exponential backoff
    """

    def __init__(self):
        self._targets: Dict[str, dict] = {}

    def register(self, name: str, base_interval_seconds: int = 3600, priority: str = "medium"):
        self._targets[name] = {
            "base_interval": base_interval_seconds,
            "current_interval": base_interval_seconds,
            "priority": priority,
            "history": deque(maxlen=20),
            "change_rate": 0.0,
            "failure_count": 0,
            "total_checks": 0,
            "last_adjusted": None,
        }

    def record_success(self, name: str, changed: bool = False, events_count: int = 0):
        if name not in self._targets:
            return
        t = self._targets[name]
        t["history"].append({"changed": changed, "events": events_count, "time": datetime.now()})
        t["failure_count"] = 0
        t["total_checks"] += 1
        self._recalc(name)

    def record_failure(self, name: str, error: str = ""):
        if name not in self._targets:
            return
        t = self._targets[name]
        t["failure_count"] += 1
        t["history"].append({"changed": False, "events": 0, "time": datetime.now(), "error": error})
        t["total_checks"] += 1
        self._recalc(name)

    def _recalc(self, name: str):
        t = self._targets[name]
        history = t["history"]
        if len(history) < 2:
            t["change_rate"] = 0.0
            return

        recent = list(history)[-10:]
        changes = sum(1 for h in recent if h.get("changed"))
        t["change_rate"] = changes / len(recent)

        # Adjust interval based on change rate
        base = t["base_interval"]
        if t["failure_count"] >= 3:
            multiplier = min(2 ** t["failure_count"], 8)
            t["current_interval"] = min(base * multiplier, base * 8)
        elif t["change_rate"] > 0.5:
            t["current_interval"] = max(base // 3, 300)
        elif t["change_rate"] > 0.2:
            t["current_interval"] = max(base // 2, 600)
        elif t["change_rate"] < 0.05:
            t["current_interval"] = min(base * 2, base * 4)
        else:
            t["current_interval"] = base
        t["last_adjusted"] = datetime.now()

    def get_stats(self) -> Dict:
        targets_stats = {}
        for name, t in self._targets.items():
            targets_stats[name] = {
                "current_interval_min": round(t["current_interval"] / 60),
                "change_rate": round(t["change_rate"], 2),
                "failures": t["failure_count"],
                "total_checks": t["total_checks"],
                "priority": t["priority"],
            }
        return {"targets": targets_stats, "total_tracked": len(self._targets)}


class SchedulerService:
    """任务调度服务（集成智能动态调度）"""

    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self.jobs = {}
        self._smart_scheduler = SmartScheduler()

    @property
    def smart_scheduler(self):
        return self._smart_scheduler

    async def start(self):
        """启动调度器"""
        self.scheduler.start()
        logger.info("[Scheduler] 任务调度器已启动")

    async def shutdown(self):
        """关闭调度器"""
        self.scheduler.shutdown()
        logger.info("[Scheduler] 任务调度器已关闭")

    async def add_monitoring_job(self, competitor_id: int, frequency_minutes: int = 60,
                                  priority: str = "medium"):
        """添加监控任务（支持智能调度）"""
        job_id = f"monitor_competitor_{competitor_id}"

        # 如果任务已存在，先移除
        if job_id in self.jobs:
            await self.remove_monitoring_job(competitor_id)

        # 注册到智能调度器
        if self.smart_scheduler:
            comp_name = f"competitor_{competitor_id}"
            self.smart_scheduler.register(
                comp_name,
                base_interval_seconds=frequency_minutes * 60,
                priority=priority,
            )

        # 添加新任务
        job = self.scheduler.add_job(
            self._monitor_competitor,
            trigger=IntervalTrigger(minutes=frequency_minutes),
            id=job_id,
            args=[competitor_id],
            replace_existing=True
        )

        self.jobs[job_id] = {
            'competitor_id': competitor_id,
            'frequency': frequency_minutes,
            'priority': priority,
            'next_run': job.next_run_time
        }

        logger.info(f"[Scheduler] 添加监控任务: 竞品{competitor_id}, 频率{frequency_minutes}分钟, 优先级{priority}")
        return job_id

    async def remove_monitoring_job(self, competitor_id: int):
        """移除监控任务"""
        job_id = f"monitor_competitor_{competitor_id}"

        if job_id in self.jobs:
            self.scheduler.remove_job(job_id)
            del self.jobs[job_id]
            logger.info(f"[Scheduler] 移除监控任务: 竞品{competitor_id}")

    async def update_job_frequency(self, competitor_id: int, new_frequency: int):
        """更新任务频率"""
        priority = self.jobs.get(f"monitor_competitor_{competitor_id}", {}).get("priority", "medium")
        await self.add_monitoring_job(competitor_id, new_frequency, priority)

    async def _monitor_competitor(self, competitor_id: int):
        """监控竞品的实际执行函数 - 采集→变化检测→告警"""
        from app.services.competitor_service import competitor_service

        try:
            logger.info(f"[Monitor] 开始监控竞品 {competitor_id}")

            # 通过 competitor_service.trigger_fetch 执行采集
            # trigger_fetch 已集成 data_pipeline，完成完整闭环
            result = competitor_service.trigger_fetch(competitor_id)

            if result.get('success'):
                data = result.get('data', {})
                changes = data.get('changes', [])
                alerts = data.get('alerts_triggered', 0)
                has_changes = len(changes) > 0

                # 记录到智能调度器
                if self.smart_scheduler:
                    comp_name = f"competitor_{competitor_id}"
                    self.smart_scheduler.record_success(
                        comp_name,
                        changed=has_changes,
                        events_count=data.get('fetched', 0),
                    )
                    # 动态调整频率
                    await self._maybe_adjust_frequency(competitor_id)

                logger.info(
                    f"[Monitor] 竞品 {competitor_id} 采集完成: "
                    f"events={data.get('fetched', 0)}, changes={len(changes)}, alerts={alerts}"
                )
            else:
                # 采集失败，记录到智能调度器
                if self.smart_scheduler:
                    comp_name = f"competitor_{competitor_id}"
                    self.smart_scheduler.record_failure(
                        comp_name,
                        error=result.get('error', 'unknown')
                    )
                    await self._maybe_adjust_frequency(competitor_id)

                logger.warning(f"[Monitor] 竞品 {competitor_id} 采集失败: {result.get('error')}")

        except Exception as e:
            logger.error(f"[Monitor] 监控竞品 {competitor_id} 异常: {e}")
            if self.smart_scheduler:
                comp_name = f"competitor_{competitor_id}"
                self.smart_scheduler.record_failure(comp_name, error=str(e))

    async def _maybe_adjust_frequency(self, competitor_id: int):
        """根据智能调度器的建议动态调整采集频率"""
        if not self.smart_scheduler:
            return

        comp_name = f"competitor_{competitor_id}"
        schedule = self.smart_scheduler._targets.get(comp_name)
        if not schedule:
            return

        # 将秒转换为分钟
        new_interval_minutes = max(1, schedule.current_interval // 60)

        job_id = f"monitor_competitor_{competitor_id}"
        current_freq = self.jobs.get(job_id, {}).get('frequency', 0)

        # 频率变化超过20%时才调整，避免频繁重建任务
        if current_freq and abs(new_interval_minutes - current_freq) / max(current_freq, 1) > 0.2:
            priority = self.jobs.get(job_id, {}).get('priority', 'medium')
            await self.add_monitoring_job(competitor_id, new_interval_minutes, priority)
            logger.info(
                f"[Scheduler] 动态调整: 竞品{competitor_id} "
                f"频率 {current_freq}min → {new_interval_minutes}min "
                f"(change_rate={schedule.change_rate:.2f})"
            )

    def get_jobs(self) -> Dict:
        """获取所有任务"""
        result = dict(self.jobs)
        # 附加智能调度统计
        if self.smart_scheduler:
            result['_smart_stats'] = self.smart_scheduler.get_stats()
        return result

    def get_job_status(self, competitor_id: int) -> Optional[Dict]:
        """获取任务状态"""
        job_id = f"monitor_competitor_{competitor_id}"
        status = self.jobs.get(job_id)
        if status and self.smart_scheduler:
            comp_name = f"competitor_{competitor_id}"
            schedule = self.smart_scheduler._targets.get(comp_name)
            if schedule:
                status['smart_interval'] = schedule.current_interval
                status['change_rate'] = round(schedule.change_rate, 2)
                status['failures'] = schedule.failure_count
        return status


# 全局服务实例
scheduler_service = SchedulerService()
