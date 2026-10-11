"""HTTP client for the dirty-leds server (python/lib/server.py)"""
import json
import time
from collections.abc import Callable

import aiohttp

from .const import FEATURES_SECONDS


class DirtyLedsError(Exception):
    """The server could not be reached or refused an action"""


class DirtyLedsClient:
    def __init__(self, session: aiohttp.ClientSession, host: str, port: int) -> None:
        self._session = session
        self.base_url = f"http://{host}:{port}"

    async def get_state(self) -> dict:
        try:
            async with self._session.get(f"{self.base_url}/api/state", timeout=aiohttp.ClientTimeout(total=10)) as response:
                response.raise_for_status()
                return await response.json()
        except (aiohttp.ClientError, TimeoutError) as error:
            raise DirtyLedsError(f"Cannot reach dirty-leds at {self.base_url}: {error}") from error

    async def action(self, name: str, payload: dict) -> None:
        try:
            async with self._session.post(
                f"{self.base_url}/api/action",
                json={"action": name, "payload": payload},
                timeout=aiohttp.ClientTimeout(total=10),
            ) as response:
                body = await response.json(content_type=None)
        except (aiohttp.ClientError, TimeoutError) as error:
            raise DirtyLedsError(f"Cannot reach dirty-leds at {self.base_url}: {error}") from error
        if response.status != 200:
            raise DirtyLedsError(body.get("error", f"HTTP {response.status}"))

    async def stream(self, on_state: Callable[[dict], None], on_features: Callable[[dict], None]) -> None:
        """Follow the event stream until it closes. Frames are skipped unless a features reading is due"""
        timeout = aiohttp.ClientTimeout(total=None, sock_connect=10, sock_read=60)
        async with self._session.get(f"{self.base_url}/api/events", timeout=timeout) as response:
            response.raise_for_status()
            event = None
            features_at = 0.0
            async for raw in response.content:
                line = raw.decode().rstrip("\n")
                if line.startswith("event: "):
                    event = line[len("event: "):]
                elif line.startswith("data: "):
                    if event == "state":
                        on_state(json.loads(line[len("data: "):]))
                    elif event == "frame" and time.monotonic() - features_at >= FEATURES_SECONDS:
                        features_at = time.monotonic()
                        frame = json.loads(line[len("data: "):])
                        frame.pop("leds", None)
                        on_features(frame)
