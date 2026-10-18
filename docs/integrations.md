# 官方接口核查（2026-10-16）

## AnySearch

- [Authentication](https://www.anysearch.com/docs/auth)：匿名或 Bearer key；错误 key 不自动退回匿名。
- [POST /v1/search](https://www.anysearch.com/docs/api-endpoints/v1-search)：JSON `query`, `max_results` (1–10), `language`, `format`; 响应 `code=0`, `data.results[].title/url/snippet/content`。
- 402 可能返回账号、密码、API key，因此适配器丢弃供应商错误消息，只返回本地枚举错误码。重试不能将这类返回体写入日志。
- 真实测试 query 为公开概念“月亮 圆缺 月相 原因 科学”，无儿童数据。返回 5 个可追溯来源，包含中央气象署儿童科普及教育网文章。检索返回不代表已独立核对内容，也不证明模型依据了这些来源。

## Xingyun

- [SDK 接入说明](https://www.xingyun3d.com/developers/52-183)
- [快速开始](https://www.xingyun3d.com/developers/59-502)
- [安装与集成](https://www.xingyun3d.com/developers/59-503)

官方 CDN：`https://media.xingyun3d.com/xingyun3d/general/litesdk/xmovAvatar@latest.js`。
使用正式记录的 `init({onDownloadProgress})`, `speak(text, true, true)`, `interactiveidle()`, `destroy()`。
SDK 文档存在版本差异：音频状态同时记载 `start/end` 和 `voice_start/voice_end`，适配器兼容两组。SDK 默认处理 subtitle_on/off，未覆写字幕事件。实际播放仍须真机测试。

`@latest` 是官方提供入口，可能变更。发布前应依据真实测试固定供应商确认的 SDK 版本，不猜测版本号。

公开快速开始需要客户端 App ID/Secret。未发现足以实现安全 token 交换的官方协议；SDK 虽允许自定义 gatewayServer/headers，但这本身不证明可以安全代理鉴权。故默认禁用下发；不能把缺少凭证描述为已接入成功。需要项目负责人/赞助商确认浏览器凭证范围或正式安全鉴权方案。

## 模型

OpenAI-compatible JSON chat adapter，不依赖某特定模型 SDK。需要模型名、API 基础地址、服务端 API key，并支持 JSON object 返回。意图分析和讲解分开，模型输入包含明确年级和教学策略。模型生成的来源 ID 必须存在于实际检索结果；页面链接仅来自检索适配器。

当前只有 mocked HTTP 合约验证，未使用真实模型凭证。服务端安全规则不能保证拦截所有隐私表达/提示注入，不能声称生产级儿童安全或教育有效性。
