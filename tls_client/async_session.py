from .response import Response
from .sessions import Session

import asyncio
import functools


class AsyncSession(Session):
    """``Session`` whose requests can be awaited.

    The native call blocks, so each request runs in the default thread pool
    executor; ctypes releases the GIL during the call, so concurrent requests
    (e.g. ``asyncio.gather``) run in parallel. Takes the same arguments as
    ``Session``; ``get``/``post``/... are inherited and return awaitables.
    """

    async def execute_request(self, *args, **kwargs) -> Response:
        loop = asyncio.get_running_loop()
        call = functools.partial(super().execute_request, *args, **kwargs)
        return await loop.run_in_executor(None, call)

    async def aclose(self) -> str:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self.close)

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        await self.aclose()
