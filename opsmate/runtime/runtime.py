from abc import ABC, abstractmethod
import asyncio


class Runtime(ABC):
    @abstractmethod
    async def run(self, *args, **kwargs):
        pass

    @abstractmethod
    async def connect(self):
        pass

    @abstractmethod
    async def disconnect(self):
        pass


class RuntimeError(Exception): ...
