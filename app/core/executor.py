from concurrent.futures import ThreadPoolExecutor
import asyncio
from functools import wraps
from typing import Callable, Any
from app.core.config import settings

# 全局线程池执行器
executor = ThreadPoolExecutor(
    max_workers=settings.max_workers,
    thread_name_prefix="api_worker"
)

def run_sync(func: Callable) -> Callable:
    """
    装饰器：将同步函数包装为异步执行

    用法：
        @run_sync
        def sync_function():
            return result

        async def async_endpoint():
            result = await sync_function()
            return result
    """
    @wraps(func)
    async def wrapper(*args, **kwargs) -> Any:
        loop = asyncio.get_event_loop()
        if kwargs:
            # 如果有kwargs，需要用lambda包装
            return await loop.run_in_executor(
                executor,
                lambda: func(*args, **kwargs)
            )
        else:
            return await loop.run_in_executor(executor, func, *args)
    return wrapper

async def run_sync_function(func: Callable, *args, **kwargs) -> Any:
    """
    直接包装同步函数为异步执行

    用法：
        result = await run_sync_function(get_competitors_sync, db)
    """
    loop = asyncio.get_event_loop()
    if kwargs:
        # 如果有kwargs，需要用lambda包装
        return await loop.run_in_executor(
            executor,
            lambda: func(*args, **kwargs)
        )
    else:
        return await loop.run_in_executor(executor, func, *args)