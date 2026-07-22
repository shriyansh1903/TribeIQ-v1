import abc
from typing import Callable, Any

class BackgroundJobService(abc.ABC):
    @abc.abstractmethod
    def enqueue(self, func: Callable, *args, **kwargs) -> Any:
        """Enqueues a function for background execution."""
        pass

class ThreadPoolBackgroundJobService(BackgroundJobService):
    def __init__(self, max_workers: int = 5):
        from concurrent.futures import ThreadPoolExecutor
        self._executor = ThreadPoolExecutor(max_workers=max_workers)

    def enqueue(self, func: Callable, *args, **kwargs) -> Any:
        return self._executor.submit(func, *args, **kwargs)

# Global background job service instance
background_job_service = ThreadPoolBackgroundJobService()
