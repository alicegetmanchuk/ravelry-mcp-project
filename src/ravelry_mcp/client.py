import os
from dotenv import load_dotenv
import httpx

load_dotenv()

BASE_URL = "https://api.ravelry.com"


class RavelryClient:
    def __init__(self):
        username = os.environ["RAVELRY_USERNAME"]
        password = os.environ["RAVELRY_PASSWORD"]
        self._client = httpx.AsyncClient(
            base_url=BASE_URL,
            auth=(username, password),
        )

    async def get(self, endpoint: str, params: dict | None = None) -> dict:
        response = await self._client.get(endpoint, params=params)
        response.raise_for_status()
        return response.json()

    async def close(self):
        await self._client.aclose()

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        await self.close()
