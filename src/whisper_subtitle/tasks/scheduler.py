"""Task scheduler for background processing."""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class TaskStatus(Enum):
    """Task status enumeration."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class ScheduledTask:
    """Scheduled task data class."""
    id: str
    name: str
    func: Callable
    args: tuple = field(default_factory=tuple)
    kwargs: dict = field(default_factory=dict)
    schedule_time: datetime = field(default_factory=datetime.now)
    interval: Optional[timedelta] = None
    max_retries: int = 3
    retry_count: int = 0
    status: TaskStatus = TaskStatus.PENDING
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result: Any = None
    error: Optional[str] = None
    next_run: Optional[datetime] = None


class TaskScheduler:
    """Background task scheduler."""
    
    def __init__(self):
        self.tasks: Dict[str, ScheduledTask] = {}
        self.running = False
        self._scheduler_task: Optional[asyncio.Task] = None
        self._lock = asyncio.Lock()
    
    async def start(self):
        """Start the task scheduler."""
        if self.running:
            logger.warning("Task scheduler is already running")
            return
        
        self.running = True
        self._scheduler_task = asyncio.create_task(self._scheduler_loop())
        logger.info("Task scheduler started")
    
    async def stop(self):
        """Stop the task scheduler."""
        if not self.running:
            return
        
        self.running = False
        
        if self._scheduler_task:
            self._scheduler_task.cancel()
            try:
                await self._scheduler_task
            except asyncio.CancelledError:
                pass
        
        # Cancel all pending tasks
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
        """Schedule a task for execution.
        
        Args:
            task_id: Unique task identifier
            name: Task name
            func: Function to execute
            args: Function arguments
            kwargs: Function keyword arguments
            schedule_time: When to run the task (default: now)
            interval: Repeat interval (None for one-time task)
            max_retries: Maximum retry attempts
        
        Returns:
            Task ID
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
        """Cancel a scheduled task.
        
        Args:
            task_id: Task ID to cancel
        
        Returns:
            True if task was cancelled, False if not found or already completed
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
        """Get task status.
        
        Args:
            task_id: Task ID
        
        Returns:
            Task object or None if not found
        """
        async with self._lock:
            return self.tasks.get(task_id)
    
    async def list_tasks(
        self,
        status: Optional[TaskStatus] = None,
        limit: Optional[int] = None
    ) -> List[ScheduledTask]:
        """List tasks.
        
        Args:
            status: Filter by status
            limit: Maximum number of tasks to return
        
        Returns:
            List of tasks
        """
        async with self._lock:
            tasks = list(self.tasks.values())
        
        if status:
            tasks = [task for task in tasks if task.status == status]
        
        # Sort by creation time (newest first)
        tasks.sort(key=lambda t: t.created_at, reverse=True)
        
        if limit:
            tasks = tasks[:limit]
        
        return tasks
    
    async def cleanup_old_tasks(self, older_than: timedelta = timedelta(days=7)):
        """Clean up old completed/failed tasks.
        
        Args:
            older_than: Remove tasks older than this duration
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
        """Main scheduler loop."""
        logger.info("Scheduler loop started")
        
        while self.running:
            try:
                await self._process_pending_tasks()
                await asyncio.sleep(1)  # Check every second
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in scheduler loop: {str(e)}")
                await asyncio.sleep(5)  # Wait before retrying
        
        logger.info("Scheduler loop stopped")
    
    async def _process_pending_tasks(self):
        """Process pending tasks that are ready to run."""
        now = datetime.now()
        tasks_to_run = []
        
        async with self._lock:
            for task in self.tasks.values():
                if (task.status == TaskStatus.PENDING and 
                    task.next_run and task.next_run <= now):
                    tasks_to_run.append(task)
        
        # Run tasks outside the lock to avoid blocking
        for task in tasks_to_run:
            asyncio.create_task(self._execute_task(task))
    
    async def _execute_task(self, task: ScheduledTask):
        """Execute a single task."""
        async with self._lock:
            if task.status != TaskStatus.PENDING:
                return  # Task was cancelled or already running
            
            task.status = TaskStatus.RUNNING
            task.started_at = datetime.now()
        
        logger.info(f"Executing task: {task.name} (ID: {task.id})")
        
        try:
            # Execute the task function
            if asyncio.iscoroutinefunction(task.func):
                result = await task.func(*task.args, **task.kwargs)
            else:
                # Run synchronous function in thread pool
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(
                    None, lambda: task.func(*task.args, **task.kwargs)
                )
            
            async with self._lock:
                task.status = TaskStatus.COMPLETED
                task.result = result
                task.completed_at = datetime.now()
                
                # Schedule next run if this is a recurring task
                if task.interval:
                    task.next_run = datetime.now() + task.interval
                    task.status = TaskStatus.PENDING
                    task.retry_count = 0  # Reset retry count for recurring tasks
            
            logger.info(f"Task completed successfully: {task.name} (ID: {task.id})")
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Task failed: {task.name} (ID: {task.id}): {error_msg}")
            
            async with self._lock:
                task.retry_count += 1
                task.error = error_msg
                
                if task.retry_count < task.max_retries:
                    # Schedule retry
                    retry_delay = timedelta(minutes=2 ** task.retry_count)  # Exponential backoff
                    task.next_run = datetime.now() + retry_delay
                    task.status = TaskStatus.PENDING
                    logger.info(f"Task will be retried in {retry_delay}: {task.name} (ID: {task.id})")
                else:
                    # Max retries reached
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
        """Schedule a recurring task.
        
        Args:
            task_id: Unique task identifier
            name: Task name
            func: Function to execute
            interval: Repeat interval
            args: Function arguments
            kwargs: Function keyword arguments
            start_time: When to start (default: now)
            max_retries: Maximum retry attempts per execution
        
        Returns:
            Task ID
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
        """Schedule a daily recurring task.
        
        Args:
            task_id: Unique task identifier
            name: Task name
            func: Function to execute
            hour: Hour to run (0-23)
            minute: Minute to run (0-59)
            args: Function arguments
            kwargs: Function keyword arguments
            max_retries: Maximum retry attempts per execution
        
        Returns:
            Task ID
        """
        # Calculate next run time
        now = datetime.now()
        next_run = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        
        # If the time has already passed today, schedule for tomorrow
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