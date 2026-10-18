import asyncio
from contextlib import asynccontextmanager
from pathlib import Path
import httpx
from fastapi import FastAPI, Request, Response, HTTPException
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from .config import Settings
from .store import Store
from .search import AnySearch
from .llm import LLM
from .demo import DemoGenerator
from .agent import Agent, public_state
from .models import SessionInput, Turn

COOKIE = 'spark_session'

def create_app(settings=None, client=None):
    settings = settings or Settings()
    store = Store(settings.database_path,settings.session_ttl_seconds)
    owned_client = client is None
    client = client or httpx.AsyncClient()
    agent = Agent(DemoGenerator() if settings.app_mode=='demo' else LLM(settings,client),AnySearch(settings,client),store,settings.app_mode)
    # Bounded stripes serialize turns/deletion for the same anonymous session.
    locks = [asyncio.Lock() for _ in range(64)]
    @asynccontextmanager
    async def lifespan(app):
        async def clean():
            while True:
                await asyncio.sleep(60)
                store.purge()
        job = asyncio.create_task(clean())
        yield
        job.cancel()
        try: await job
        except asyncio.CancelledError: pass
        if owned_client: await client.aclose()
    app = FastAPI(title='星火同学',lifespan=lifespan)
    app.state.store,app.state.agent = store,agent
    @app.middleware('http')
    async def headers(request, call_next):
        if request.method in ('POST','DELETE'):
            origin = request.headers.get('origin')
            if origin and origin != str(request.base_url).rstrip('/'):
                return JSONResponse({'detail':'不允许跨站请求'},status_code=403)
        response = await call_next(request)
        response.headers['Cache-Control'] = 'no-store'
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['Referrer-Policy'] = 'no-referrer'
        return response
    def session(request):
        sid = request.cookies.get(COOKIE,'')
        state = store.get(sid)
        if not state: raise HTTPException(401,'本次学习已结束，请重新开始。')
        return sid,state
    @app.get('/api/health')
    def health():
        return {'status':'ok','mode':settings.app_mode,
            'llm_configured':bool(settings.llm_api_key and settings.llm_model),
            'search':'live', 'avatar_configured':bool(settings.xingyun_app_id and settings.xingyun_app_secret and settings.xingyun_browser_auth_approved)}
    @app.post('/api/session')
    def start(body:SessionInput,request:Request,response:Response):
        old = request.cookies.get(COOKIE)
        if old: store.delete(old)
        sid = store.create(body.grade,settings.app_mode)
        response.set_cookie(COOKIE,sid,httponly=True,secure=settings.cookie_secure,samesite='strict',max_age=settings.session_ttl_seconds)
        return public_state(store.get(sid))
    @app.get('/api/session')
    def current(request:Request):
        return public_state(session(request)[1])
    @app.delete('/api/session')
    async def end(request:Request,response:Response):
        sid = request.cookies.get(COOKIE,'')
        async with locks[hash(sid)%len(locks)]: store.delete(sid)
        response.delete_cookie(COOKIE)
        return {'deleted':True}
    @app.post('/api/turn')
    async def chat(body:Turn,request:Request):
        sid = request.cookies.get(COOKIE,'')
        async with locks[hash(sid)%len(locks)]:
            sid,state = session(request)
            try:
                result = await asyncio.wait_for(agent.turn(state,body),timeout=settings.turn_timeout_seconds)
            except asyncio.TimeoutError:
                raise HTTPException(504,'这次等待有点久，请稍后再试。') from None
            store.save(sid,state)
            return result
    @app.get('/api/impact')
    def impact():
        return {'live':store.metrics('live'),'demo':store.metrics('demo'),
                'note':'仅统计参与情况与自我报告，不代表已验证的教育效果。话题数为各会话探索次数之和，不是独立知识点数。'}
    @app.get('/api/avatar/config')
    def avatar(request:Request):
        session(request)
        if not settings.xingyun_browser_auth_approved:
            raise HTTPException(503,'数字人尚未启用，可以继续文字学习。')
        if not (settings.xingyun_app_id and settings.xingyun_app_secret):
            raise HTTPException(503,'数字人尚未配置，可以继续文字学习。')
        # This explicit opt-in is only for sponsor-approved browser-scoped credentials.
        return {'appId':settings.xingyun_app_id,'appSecret':settings.xingyun_app_secret,
                'gatewayServer':'https://nebula-agent.xingyun3d.com/user/v1/ttsa/session'}
    dist = Path('frontend/dist').resolve()
    if dist.exists(): app.mount('/',StaticFiles(directory=dist,html=True),name='frontend')
    return app

app = create_app()
