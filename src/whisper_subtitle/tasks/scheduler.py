"""Task scheduler for background processing."""

# 导入标准库模块
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass, field
from enum import Enum

# 配置日志记录
logger = logging.getLogger(__name__)


class TaskStatus(Enum):
    """任务状态枚举"""
    PENDING = "pending"      # 待处理
    RUNNING = "running"      # 运行中
    COMPLETED = "completed"  # 已完成
    FAILED = "failed"        # 失败
    CANCELLED = "cancelled"  # 已取消


@dataclass
class ScheduledTask:
    """调度任务数据类，表示一个计划任务"""
    id: str                  # 任务唯一标识
    name: str                # 任务名称
    func: Callable           # 要执行的函数
    args: tuple = field(default_factory=tuple)  # 函数位置参数
    kwargs: dict = field(default_factory=dict)  # 函数关键字参数
    schedule_time: datetime = field(default_factory=datetime.now)  # 计划执行时间
    interval: Optional[timedelta] = None        # 重复间隔
    max_retries: int = 3                        # 最大重试次数
    retry_count: int = 0                        # 已重试次数
    status: TaskStatus = TaskStatus.PENDING     # 当前状态
    created_at: datetime = field(default_factory=datetime.now)  # 创建时间
    started_at: Optional[datetime] = None       # 开始时间
    completed_at: Optional[datetime] = None     # 完成时间
    result: Any = None                          # 执行结果
    error: Optional[str] = None                 # 错误信息
    next_run: Optional[datetime] = None         # 下次运行时间


class TaskScheduler:
    """后台任务调度器"""
    
    def __init__(self):
        """初始化任务调度器"""
        self.tasks: Dict[str, ScheduledTask] = {}  # 存储所有任务
        self.running = False                       # 调度器运行状态
        self._scheduler_task: Optional[asyncio.Task] = None  # 调度任务
        self._lock = asyncio.Lock()                # 异步锁，用于线程安全操作
    
    async def start(self):
        """启动任务调度器"""
        if self.running:
            logger.warning("Task scheduler is already running")
            return
        
        self.running = True
        self._scheduler_task = asyncio.create_task(self._scheduler_loop())
        logger.info("Task scheduler started")
    
    async def stop(self):
        """停止任务调度器"""
        if not self.running:
            return
        
        self.running = False
        
        if self._scheduler_task:
            self._scheduler_task.cancel()
            try:
                await self._scheduler_task
            except asyncio.CancelledError:
                pass
        
        # 取消所有待处理任务
        async with self._lock:
            for task in self.tasks.values():
                if task.status == TaskStatus.RUNNING:
                    task.status = TaskStatus.CANCELLED
                    task.error = "Scheduler stopped"
                    task.completed_at = datetime.now()
        
        logger.info("Task scheduler stopped")
    
    async def schedule_task(
        self,
        task_id: str,
        name: str,
        func: Callable,
        args: tuple = (),
        kwargs: dict = None,
        schedule_time: Optional[datetime] = None,
        interval: Optional[timedelta] = None,
        max_retries: int = 3
    ) -> str:
        """调度一个任务以执行。
        
        参数:
            task_id: 任务唯一标识
            name: 任务名称
            func: 要执行的函数
            args: 函数位置参数
            kwargs: 函数关键字参数
            schedule_time: 任务执行时间(默认:现在)
            interval: 重复间隔(无为一次性任务)
            max_retries: 最大重试次数
        
        返回:
            任务ID
        """
        if kwargs is None:
            kwargs = {}
        
        if schedule_time is None:
            schedule_time = datetime.now()
        
        task = ScheduledTask(
            id=task_id,
            name=name,
            func=func,
            args=args,
            kwargs=kwargs,
            schedule_time=schedule_time,
            interval=interval,
            max_retries=max_retries,
            next_run=schedule_time
        )
        
        async with self._lock:
            self.tasks[task_id] = task
        
        logger.info(f"Task scheduled: {name} (ID: {task_id}) at {schedule_time}")
        return task_id
    
    async def cancel_task(self, task_id: str) -> bool:
        """取消一个已调度的任务。
        
        参数:
            task_id: 要取消的任务ID
        
        返回:
            如果任务被取消则为True，如果未找到或已完成则为False
        """
        async with self._lock:
            if task_id not in self.tasks:
                return False
            
            task = self.tasks[task_id]
            
            if task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
                return False
            
            task.status = TaskStatus.CANCELLED
            task.error = "Cancelled by user"
            task.completed_at = datetime.now()
        
        logger.info(f"Task cancelled: {task.name} (ID: {task_id})")
        return True
    
    async def get_task_status(self, task_id: str) -> Optional[ScheduledTask]:
        """获取任务状态。
        
        参数:
            task_id: 任务ID
        
        返回:
            任务对象或未找到时为None
        """
        async with self._lock:
            return self.tasks.get(task_id)
    
    async def list_tasks(
        self,
        status: Optional[TaskStatus] = None,
        limit: Optional[int] = None
    ) -> List[ScheduledTask]:
        """列出任务。
        
        参数:
            status: 状态过滤
            limit: 返回的最大任务数
        
        返回:
            任务列表
        """
        async with self._lock:
            tasks = list(self.tasks.values())
        
        if status:
            tasks = [task for task in tasks if task.status == status]
        
        # 按创建时间排序(最新在前)
        tasks.sort(key=lambda t: t.created_at, reverse=True)
        
        if limit:
            tasks = tasks[:limit]
        
        return tasks
    
    async def cleanup_old_tasks(self, older_than: timedelta = timedelta(days=7)):
        """清理旧的已完成/失败的任务。
        
        参数:
            older_than: 移除比这个时间更早的任务
        """
        cutoff_time = datetime.now() - older_than
        
        async with self._lock:
            tasks_to_remove = []
            
            for task_id, task in self.tasks.items():
                if (task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED] and
                    task.completed_at and task.completed_at < cutoff_time):
                    tasks_to_remove.append(task_id)
            
            for task_id in tasks_to_remove:
                del self.tasks[task_id]
        
        if tasks_to_remove:
            logger.info(f"Cleaned up {len(tasks_to_remove)} old tasks")
    
    async def _scheduler_loop(self):
        """主调度循环"""
        logger.info("Scheduler loop started")
        
        while self.running:
            try:
                await self._process_pending_tasks()
                await asyncio.sleep(1)  # 每秒检查一次
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in scheduler loop: {str(e)}")
                await asyncio.sleep(5)  # 等待后重试
        
        logger.info("Scheduler loop stopped")
    
    async def _process_pending_tasks(self):
        """处理待执行的任务"""
        now = datetime.now()
        tasks_to_run = []
        
        async with self._lock:
            for task in self.tasks.values():
                if (task.status == TaskStatus.PENDING and 
                    task.next_run and task.next_run <= now):
                    tasks_to_run.append(task)
        
        # 在锁外运行任务以避免阻塞
        for task in tasks_to_run:
            asyncio.create_task(self._execute_task(task))
    
    async def _execute_task(self, task: ScheduledTask):
        """执行单个任务"""
        async with self._lock:
            if task.status != TaskStatus.PENDING:
                return  # 任务被取消或正在运行
            
            task.status = TaskStatus.RUNNING
            task.started_at = datetime.now()
        
        logger.info(f"Executing task: {task.name} (ID: {task.id})")
        
        try:
            # 执行任务函数
            if asyncio.iscoroutinefunction(task.func):
                result = await task.func(*task.args, **task.kwargs)
            else:
                # 在线程池中运行同步函数
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(
                    None, lambda: task.func(*task.args, **task.kwargs)
                )
            
            async with self._lock:
                task.status = TaskStatus.COMPLETED
                task.result = result
                task.completed_at = datetime.now()
                
                # 如果是周期性任务，安排下次运行
                if task.interval:
                    task.next_run = datetime.now() + task.interval
                    task.status = TaskStatus.PENDING
                    task.retry_count = 0  # 重置周期性任务的重试计数
            
            logger.info(f"Task completed successfully: {task.name} (ID: {task.id})")
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Task failed: {task.name} (ID: {task.id}): {error_msg}")
            
            async with self._lock:
                task.retry_count += 1
                task.error = error_msg
                
                if task.retry_count < task.max_retries:
                    # 安排重试
                    retry_delay = timedelta(minutes=2 ** task.retry_count)  # 指数退避
                    task.next_run = datetime.now() + retry_delay
                    task.status = TaskStatus.PENDING
                    logger.info(f"Task will be retried in {retry_delay}: {task.name} (ID: {task.id})")
                else:
                    # 达到最大重试次数
                    task.status = TaskStatus.FAILED
                    task.completed_at = datetime.now()
                    logger.error(f"Task failed permanently after {task.retry_count} retries: {task.name} (ID: {task.id})")
    
    async def schedule_recurring_task(
        self,
        task_id: str,
        name: str,
        func: Callable,
        interval: timedelta,
        args: tuple = (),
        kwargs: dict = None,
        start_time: Optional[datetime] = None,
        max_retries: int = 3
    ) -> str:
        """调度一个周期性任务。
        
        参数:
            task_id: 任务唯一标识
            name: 任务名称
            func: 要执行的函数
            interval: 重复间隔
            args: 函数位置参数
            kwargs: 函数关键字参数
            start_time: 开始时间(默认:现在)
            max_retries: 每次执行的最大重试次数
        
        返回:
            任务ID
        """
        return await self.schedule_task(
            task_id=task_id,
            name=name,
            func=func,
            args=args,
            kwargs=kwargs,
            schedule_time=start_time,
            interval=interval,
            max_retries=max_retries
        )
    
    async def schedule_daily_task(
        self,
        task_id: str,
        name: str,
        func: Callable,
        hour: int = 0,
        minute: int = 0,
        args: tuple = (),
        kwargs: dict = None,
        max_retries: int = 3
    ) -> str:
        """调度一个每日周期性任务。
        
        参数:
            task_id: 任务唯一标识
            name: 任务名称
            func: 要执行的函数
            hour: 执行小时(0-23)
            minute: 执行分钟(0-59)
            args: 函数位置参数
            kwargs: 函数关键字参数
            max_retries: 每次执行的最大重试次数
        
        返回:
            任务ID
        """
        # 计算下次运行时间
        now = datetime.now()
        next_run = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        
        # 如果时间已经过去，则安排在明天
        if next_run <= now:
            next_run += timedelta(days=1)
        
        return await self.schedule_task(
            task_id=task_id,
            name=name,
            func=func,
            args=args,
            kwargs=kwargs,
            schedule_time=next_run,
            interval=timedelta(days=1),
            max_retries=max_retries
        )