"""Makes one real adapter request. Never logs provider error bodies or credentials."""
import asyncio
import json
import httpx
from spark.config import Settings
from spark.search import AnySearch,ServiceError

async def main():
    async with httpx.AsyncClient() as client:
        try:
            sources=await AnySearch(Settings(),client).search('月亮 圆缺 月相 原因 科学')
            print(json.dumps({'status':'ok','sources':[s.model_dump(mode='json') for s in sources]},ensure_ascii=False,indent=2))
        except ServiceError as exc:
            print(json.dumps({'status':'blocked','code':exc.code}))
            raise SystemExit(1)

asyncio.run(main())
