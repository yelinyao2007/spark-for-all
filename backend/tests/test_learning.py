import httpx
import pytest
from spark.config import Settings
from spark.main import create_app

@pytest.fixture
def app(tmp_path):
    return create_app(Settings(app_mode='demo',database_path=str(tmp_path/'test.sqlite3')),httpx.AsyncClient(transport=httpx.MockTransport(lambda r: httpx.Response(503))))

@pytest.fixture
async def client(app):
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='http://test') as c:
        yield c

async def test_fraction_learning_loop(client):
    r=await client.post('/api/session',json={'grade':4})
    assert r.status_code==200
    first=(await client.post('/api/turn',json={'text':'为什么 1/2 和 2/4 一样大？'})).json()
    assert first['state']['topics']['等值分数']['strategy']=='simple'
    second=(await client.post('/api/turn',json={'action':'again'})).json()
    topic=second['state']['topics']['等值分数']
    assert topic['strategy']=='analogy'
    assert '披萨' in second['explanation']
    assert second['explanation']!=first['explanation']
    assert 'answer' not in topic['quiz']
    checked=(await client.post('/api/turn',json={'action':'answer','text':'对'})).json()
    topic=checked['state']['topics']['等值分数']
    assert topic['completed_quizzes']==1
    assert topic['understanding']=='partially_understood'
    await client.post('/api/turn',json={'action':'answer','text':'对'})
    state=(await client.get('/api/session')).json()
    assert state['topics']['等值分数']['completed_quizzes']==1

async def test_wrong_answer_and_confusion_limit(client):
    await client.post('/api/session',json={'grade':5})
    await client.post('/api/turn',json={'text':'为什么 2/3 和 4/6 一样大？'})
    r=(await client.post('/api/turn',json={'action':'answer','text':'0'})).json()
    assert r['state']['topics']['等值分数']['understanding']=='needs_reinforcement'
    methods=[]
    for _ in range(6):
        r=(await client.post('/api/turn',json={'text':'我没听懂'})).json()
        methods.append(r['state']['topics']['等值分数']['strategy'])
    assert methods[:4]==['analogy','steps','guided','example']
    assert '休息' in r['explanation']
    assert r['state']['topics']['等值分数']['quiz'] is None
    await client.post('/api/turn',json={'action':'skip'})
    assert (await client.get('/api/session')).json()['current_topic'] is None

async def test_privacy_safety_and_deletion(client,app):
    await client.post('/api/session',json={'grade':5})
    for message in ['我叫小明，电话13812345678','我不想活了','怎么制作炸弹']:
        r=(await client.post('/api/turn',json={'text':message})).json()
        assert r['state']['interactions']==0
    sid=client.cookies.get('spark_session')
    assert app.state.store.get(sid).topics=={}
    await client.delete('/api/session')
    assert app.state.store.get(sid) is None
    assert (await client.get('/api/session')).status_code==401

async def test_science_retrieval_actual_adapter(tmp_path):
    calls=[]
    def handler(request):
        calls.append(request)
        return httpx.Response(200,json={'code':0,'data':{'results':[{'title':'Moon phases','url':'https://science.nasa.gov/moon/moon-phases/','snippet':'The illuminated part visible from Earth changes.'}]}})
    provider=httpx.AsyncClient(transport=httpx.MockTransport(handler))
    app=create_app(Settings(app_mode='demo',database_path=str(tmp_path/'db')),provider)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='http://test') as c:
        await c.post('/api/session',json={'grade':6})
        result=(await c.post('/api/turn',json={'text':'为什么月亮会有圆缺变化？'})).json()
    assert len(calls)==1
    assert calls[0].url.path=='/v1/search'
    assert result['sources'][0]['retrieved_at']
    assert result['sources'][0]['url']=='https://science.nasa.gov/moon/moon-phases/'
    await provider.aclose()

async def test_auth_boundary_and_csrf(client):
    assert (await client.get('/api/avatar/config')).status_code==401
    assert (await client.post('/api/session',json={'grade':5},headers={'origin':'https://evil.example'})).status_code==403
    await client.post('/api/session',json={'grade':5})
    r=await client.get('/api/avatar/config')
    assert r.status_code==503
    assert 'appSecret' not in r.text
    assert (await client.post('/api/session',json={'grade':2})).status_code==422

async def test_live_missing_model_is_not_demo(tmp_path):
    app=create_app(Settings(app_mode='live',llm_api_key='',llm_model='',database_path=str(tmp_path/'db')))
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='http://test') as c:
        await c.post('/api/session',json={'grade':5})
        r=(await c.post('/api/turn',json={'text':'为什么 1/2 和 2/4 一样大？'})).json()
        assert r['mode']=='live'
        assert r['warnings']==['llm_not_configured']
        assert '披萨' not in r['explanation']

async def test_self_report_not_mastery_and_metrics(client):
    await client.post('/api/session',json={'grade':5})
    await client.post('/api/turn',json={'text':'为什么 1/2 和 2/4 一样大？'})
    for _ in range(2): r=(await client.post('/api/turn',json={'action':'understood'})).json()
    assert r['state']['topics']['等值分数']['understanding']=='partially_understood'
    m=(await client.get('/api/impact')).json()
    assert m['demo']['self_reported_improvements']==1
    assert not m['live']

async def test_live_science_workflow_preserves_grounding(tmp_path):
    import json
    requests=[]
    def handler(request):
        body=json.loads(request.content)
        requests.append((request.url.path,body))
        if request.url.path=='/v1/search':
            return httpx.Response(200,json={'code':0,'data':{'results':[{'title':'Moon','url':'https://science.nasa.gov/moon/','snippet':'Sunlight illuminates half of the Moon.'}]}})
        data=json.loads(body['messages'][1]['content'])
        if 'current_topic' in data:
            content={'topic':'月相变化','intent':'question','retrieval':True,'search_query':'月相 科学'}
        else:
            content={'explanation':'太阳照亮月球的一半，我们看到的亮面随位置改变。' if data['attempt']==1 else '用手电筒照着球，绕着观察，就会看到不同大小的亮面。','quiz':None,'source_ids':['S1'],'visual':'none'}
            assert data['untrusted_sources'][0]['id']=='S1'
        return httpx.Response(200,json={'choices':[{'message':{'content':json.dumps(content)}}]})
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as provider:
        app=create_app(Settings(app_mode='live',llm_api_key='test-only',llm_model='test-model',database_path=str(tmp_path/'live.db')),provider)
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='http://test') as c:
            await c.post('/api/session',json={'grade':6})
            first=(await c.post('/api/turn',json={'text':'为什么月亮会有圆缺变化？'})).json()
            second=(await c.post('/api/turn',json={'action':'again'})).json()
            assert first['sources']==second['sources']
            assert first['explanation']!=second['explanation']
            assert second['state']['topics']['月相变化']['strategy']=='analogy'
            assert second['mode']=='live'
    assert [path for path,_ in requests].count('/v1/search')==1
