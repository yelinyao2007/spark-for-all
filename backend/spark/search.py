import asyncio
from datetime import datetime, timezone
from time import monotonic
from urllib.parse import urlparse
import httpx
from .models import Source
from .safety import safe_source, safety_reply

class ServiceError(Exception):
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)

class AnySearch:
    def __init__(self, settings, client: httpx.AsyncClient):
        self.settings, self.client = settings, client
        self.cache = {}
        self.day, self.calls = '', 0
        self.lock = asyncio.Lock()

    async def search(self, query: str) -> list[Source]:
        if safety_reply(query):
            raise ServiceError('unsafe_query')
        async with self.lock:
            cached = self.cache.get(query)
            if cached and cached[0] > monotonic():
                return cached[1]
            today = datetime.now(timezone.utc).date().isoformat()
            if self.day != today:
                self.day, self.calls = today, 0
            headers = {'Authorization': f'Bearer {self.settings.anysearch_api_key}'} if self.settings.anysearch_api_key else {}
            for attempt in range(3):
                if self.calls >= self.settings.search_daily_limit:
                    raise ServiceError('search_quota')
                self.calls += 1
                try:
                    response = await self.client.post(
                        self.settings.anysearch_base_url.rstrip('/') + '/v1/search',
                        headers=headers, json={'query': query, 'max_results': 5, 'language':'zh-CN', 'format':'json'},
                        timeout=self.settings.api_timeout_seconds)
                    # Never propagate provider bodies: 402 can contain generated credentials.
                    if response.status_code in (402,429):
                        raise ServiceError('search_quota')
                    if response.status_code in (401,403):
                        raise ServiceError('search_auth')
                    if response.status_code >= 500:
                        raise httpx.ConnectError('provider unavailable')
                    response.raise_for_status()
                    payload = response.json()
                    if not isinstance(payload, dict):
                        raise ValueError('invalid envelope')
                    if payload.get('code') != 0:
                        raise ServiceError('search_response')
                    rows = payload['data']['results']
                    if not isinstance(rows, list):
                        raise ValueError()
                    sources = []
                    for row in rows[:10]:
                        if not isinstance(row, dict):
                            continue
                        url = str(row.get('url', ''))
                        parts = urlparse(url)
                        if parts.scheme not in ('https','http') or not parts.hostname or parts.username or parts.password:
                            continue
                        title = str(row.get('title') or parts.hostname)[:200]
                        snippet = str(row.get('snippet') or row.get('content') or '')[:1200]
                        if not safe_source(title + ' ' + snippet):
                            continue
                        sources.append(Source(id=f'S{len(sources)+1}', title=title, url=url,
                            snippet=snippet, retrieved_at=datetime.now(timezone.utc).isoformat()))
                    # Prefer educational and public scientific institutions without
                    # claiming that hostname alone verifies a particular statement.
                    def priority(source):
                        host = urlparse(str(source.url)).hostname or ''
                        return 0 if any(host.endswith(suffix) for suffix in ('.gov', '.gov.tw', '.edu', '.edu.cn', '.ac.cn')) else 1
                    sources.sort(key=priority)
                    if len(self.cache) >= 128:
                        self.cache.pop(next(iter(self.cache)))
                    self.cache[query] = (monotonic()+self.settings.search_cache_seconds, sources)
                    return sources
                except httpx.TransportError:
                    if attempt == 2:
                        raise ServiceError('search_unavailable') from None
                    await asyncio.sleep(0.2 * (2 ** attempt))
                except (httpx.HTTPStatusError, ValueError, KeyError, TypeError):
                    raise ServiceError('search_response') from None
            raise ServiceError('search_unavailable')
