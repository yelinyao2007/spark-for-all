# 星火同学 · Spark for All

让每一个孩子，都拥有一位愿意耐心等待他的老师。团队：微光成炬。

面向小学四至六年级的公益数学与科学 AI 学习伙伴：提问 → 理解问题 → 讲解 → 检查 → 换一种方法 → 鼓励。Vue 3 + TypeScript + Vite 前端（自托管 Noto Sans SC 中文字体），FastAPI + Pydantic + SQLite 后端。

**当前状态：可运行、已测试的 MVP 实现，但尚未达到完整验收。** AnySearch 已通过真实匿名 API 检索；真实语言模型和 Xingyun 3D 渲染仍需项目凭证及浏览器鉴权范围确认。不能把离线演示或 mock 测试当作赞助商实机验收。详细证据见 [验收清单](docs/verification.md)。

## 本地运行

需要 Python 3.11+、Node 22+；命令在本项目目录执行。无需注册账号。不要复用其他项目的密钥。

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.lock
pip install --no-deps -e .
cp .env.example .env
cd frontend
npm ci
npm run build
cd ..
uvicorn spark.main:app --host 127.0.0.1 --port 8000
```

打开 http://127.0.0.1:8000 。修改源码后重新构建前端并重启后端。

默认 `APP_MODE=live`。在 `.env` 填写 `LLM_BASE_URL`（以 `/v1` 等供应商实际基础路径结尾）、`LLM_API_KEY`、`LLM_MODEL`。供应商须支持 `/chat/completions` 和 `response_format: {"type":"json_object"}`。模型不支持 JSON 输出时会明确返回服务不可用，不暗中切换演示答案。

仅体验离线分数教学时，将 `.env` 的 `APP_MODE` 改为 `demo`。也可临时运行：

```bash
APP_MODE=demo uvicorn spark.main:app --host 127.0.0.1 --port 8000
```

此模式界面始终显示“离线演示模式”。分数讲解和检查根据输入数值及策略生成，支持不同分数；**不是通用 AI 讲解，科学问题不会返回伪装成模型生成的预写答案**。搜索依然是真实 AnySearch，联网失败会提示。真实 demo 验收必须切回 live。

开发热更新：后端用 `uvicorn ... --reload`，另一个终端执行 `cd frontend && npm run dev`，打开终端输出的本地地址。Vite 代理 `/api`，保持同源 Cookie；不要把浏览器直接指向不同域名的后端。

## 赞助商集成

### AnySearch

使用官方 `POST https://api.anysearch.com/v1/search`；可匿名，付费密钥仅放后端 `ANYSEARCH_API_KEY`。适合事实科学问题或资源请求时由 intent analyzer 触发，基础算术不搜索。将结果规范化为标题、URL、摘要、检索时间、来源 ID，页面显示可追溯链接。优先排序教育/公共科学机构，链接存在不等于事实已独立核实。

超时由 `API_TIMEOUT_SECONDS` 控制。网络失败/5xx 最多 3 次尝试，短指数退避；402/429 停止，展示额度提示；401/403 停止，不匿名重试；缓存 10 分钟、128 个查询；单进程每日调用上限默认 100。缓存与配额计数重启后清空，生产应使用共享配额存储。错误响应内容绝不进入日志或 UI（官方 402 可能包含生成的账号密钥）。

独立真实验证：

```bash
python scripts/check_live_search.py
```

### 魔珐星云 Xingyun3D

`frontend/src/services/avatar.ts` 按官方 JavaScript SDK 集成：动态加载 CDN、`new XmovAvatar`、`init`、`speak(text,true,true)`、`interactiveidle()` 打断、`destroy()` 清理；保留 SDK 默认字幕渲染，与实际音频同步。界面的文字讲解一直可读。只有主动点击“连接 3D 星火老师”才加载 SDK。

**当前鉴权限制：** 官方公开文档要求浏览器传入 `appId`、`appSecret`，本次未发现可核实的临时 token 换取协议。不能编造签名端点，也不能称“后端返回 secret”能保密。因此 `/api/avatar/config` 默认拒绝下发密钥。需要赞助商确认适用于本场景的浏览器凭证范围（独立应用、适当的额度/有效期/域名约束）或提供正式服务端鉴权协议。确认后才能使用：

```dotenv
XINGYUN_APP_ID=your-project-app-id
XINGYUN_APP_SECRET=your-approved-browser-scoped-credential
XINGYUN_BROWSER_AUTH_APPROVED=true
```

该配置意味着凭证会进入浏览器内存和网络响应，**不是秘密代理机制**。普通长期高权限密钥不符合本项目发布条件。不要仅为让画面显示而启用。当前无可用凭证，未验证真实渲染、发音、口型或字幕。SDK 需要 localhost 或 HTTPS；网络、积分、应用角色配置和浏览器能力都会影响运行。纯文字模式会销毁 SDK 连接；重连需再次点击连接按钮。

官方资料与接口限制见 [集成记录](docs/integrations.md)。

## 演示流程

**分数：** 首页选择四至六年级，点击“半块披萨的秘密”，或输入“为什么 1/2 和 2/4 一样大？”。观察简单解释 → 点击“再讲一次” → 策略变为生活类比，并显示披萨面积图 → 回答一道检查题 → 打开学习小结。可换成 2/3 与 4/6，确认不是固定对话。live 模式内容由模型生成，须验收其正确性。

“我没听懂”文字输入同样触发换策略。连续困惑 5 次后建议休息、换话题或求助真人；错误不扣分；“我懂了”仅记录自报改善。一题正确不等同掌握，多道不同题正确只显示“多次练习有进步”。短答自动检查仅接受标准文本或等值数字，不进行高风险学业评分。

**科学：** 输入“为什么月亮会有圆缺变化？” → AnySearch → 适龄讲解 → SDK 语音 → 展开实际来源。无模型时只能展示明确的服务限制；无数字人凭证时只能验证文字及检索部分，**完整场景尚不可宣称验收通过**。

## 测试

```bash
pytest -q
cd frontend
npm test
npm run build
npx playwright install chromium
```

浏览器端到端测试需要一个 **demo 模式** 的独立服务器，勿对真实使用数据库运行测试：

```bash
APP_MODE=demo DATABASE_PATH=/tmp/spark-e2e.sqlite3 uvicorn spark.main:app --host 127.0.0.1 --port 8000
# 另一个终端
cd frontend
npm run test:e2e
```

Pytest 覆盖状态切换、误答反馈、不重复计题、隐私输入、删除/过期、配额/缓存/超时、真实适配器的 mock HTTP 合约。Vitest 验证 SDK 生命周期与 SSML 转义。Playwright 在真实前后端上操作匿名分数学习和手机布局；没有替换接口，但分数生成处于明确的 demo 模式。测试不证明真实模型、数字人或教育成效。

## 隐私和边界

不注册账号，不采集位置，不建立长期儿童画像。匿名随机 HttpOnly Cookie 标识当前会话。SQLite 仅保留结构化学习状态、当前问题/上一段讲解/题目和检索来源；完整聊天历史只在页面内存。默认一小时无活动后过期，每分钟及请求时清理；点击结束立即删除当前会话。保留不含身份的计数统计，live/demo 分开。删除会话不会回滚匿名总计数。

发送前对常见身份信息、危险/困扰内容进行保守拦截；检索只发送模型提炼的概念查询，不发送完整聊天历史。检索资料被当作不可信数据，不能覆盖系统指令；外部文本不作为 HTML 渲染，模型不能创建引用链接。输出同样检查，语音内容做 SSML 转义。规则不是完整的内容安全系统，仍需真实模型红队测试、教育材料审阅和面向儿童上线前的隐私审查。浏览器语音识别可能使用浏览器供应商的云服务，界面在启用前标明，提供纯文字替代。

## 部署准备

```bash
docker compose up --build
```

构建 Vue，FastAPI 同源提供静态文件/API；SQLite 使用持久卷。Docker 配置已提供，但本机 WSL 未启用 Docker Desktop 集成，无法执行容器构建。生产放在 HTTPS 反向代理后，设置 `COOKIE_SECURE=true`，保持浏览器 Origin 与后端 Host 一致并正确配置可信代理。当前配额缓存和会话锁是单进程实现，运行一个 worker。先完成真实模型、数字人鉴权及浏览器验收，再公开部署给儿童使用。

目录：`backend/spark`（状态/Agent/服务/API）、`frontend/src`（UI/SDK）、`backend/tests`、`frontend/tests`、`docs`、`scripts`。`.github/workflows/ci.yml` 供把本目录作为独立仓库使用时启用；在当前父级多项目仓库中不会自动生效。
