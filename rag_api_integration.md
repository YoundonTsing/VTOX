# RAG 后端 API 对接手册

本手册汇总了 `http://localhost:9621` 后端的主要接口、请求/响应结构与调用示例，便于在其它项目中将该 RAG 能力作为微服务集成。前端 WebUI 通过 `/api` 前缀代理到后端同名路径，直接对接后端时无需 `/api` 前缀。

## 1. 网关与前端调用约定
- 开发环境中前端将 `/api` 代理到 `http://localhost:9621`：
  - 真实后端路径不包含 `/api` 前缀。
- 你在其他项目中直接请求后端时，使用 `http://localhost:9621/<path>`。

示例（前端代理配置）：
```
server: {
  proxy: {
    '/api': {
      target: 'http://localhost:9621',
      changeOrigin: true,
      rewrite: (path) => path.replace(/^\/api/, '')
    }
  }
}
```

## 2. 鉴权
- 多数接口依赖统一鉴权（combined_auth）。如果未配置账户/API Key，则默认“关闭鉴权”模式，直接可用。
- 若启用鉴权：
  - `GET /auth-status` 查看鉴权状态。
  - `POST /login` 登录获取 `access_token` 后，在后续请求头添加 `Authorization: Bearer <token>`。

## 3. 健康检查
- 方法/路径：`GET /health`
- 认证：通常受保护；未配置鉴权时可直接调用。
- 响应：包含系统状态、配置、流水线状态等大量字段（结构较大，前端不做二次包装）。
- 用途：探活与系统状态展示。

示例（axios）：
```ts
const resp = await axios.get('http://localhost:9621/health');
console.log(resp.data);
```

## 4. 问答（非流式）
- 方法/路径：`POST /query`
- 请求 JSON：
  - 必填：`query: string`
  - 可选：
    - `mode`: `"local" | "global" | "hybrid" | "naive" | "mix" | "bypass"`（默认 `mix`）
    - `only_need_context?: boolean`
    - `only_need_prompt?: boolean`
    - `response_type?: string`
    - `top_k?: number`
    - `chunk_top_k?: number`
    - `max_entity_tokens?: number`
    - `max_relation_tokens?: number`
    - `max_total_tokens?: number`
    - `conversation_history?: Array<{ role: 'user' | 'assistant'; content: string }>`
    - `history_turns?: number`
    - `ids?: string[]`
    - `user_prompt?: string`
    - `enable_rerank?: boolean`
- 响应 JSON：
  - 统一为：`{ "response": string }`
  - 后端会将内部对象序列化为字符串放入 `response`。

示例请求：
```json
{
  "query": "介绍一下项目架构",
  "mode": "mix",
  "top_k": 10
}
```
示例响应：
```json
{ "response": "......模型回答文本或序列化后的结果字符串......" }
```

示例（axios）：
```ts
const resp = await axios.post('http://localhost:9621/query', {
  query: '介绍一下项目架构',
  mode: 'mix',
  top_k: 10
});
console.log(resp.data.response);
```

## 5. 问答（流式，推荐）
- 方法/路径：`POST /query/stream`
- 返回内容类型：`application/x-ndjson`（逐行 JSON，非 SSE）
- 行格式示例：
```json
{"response":"第一个增量片段..."}
{"response":"第二个增量片段..."}
```
- 注意：WebUI 中示例曾对 `/query` 加 `Accept: text/event-stream`，实际后端为 NDJSON，请用 `/query/stream` 并按行解析。

示例（Node.js fetch 逐行解析）：
```ts
const res = await fetch('http://localhost:9621/query/stream', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ query: '介绍一下项目架构', mode: 'mix' })
});
for await (const chunk of res.body as any) {
  const lines = chunk.toString().trim().split('\n');
  for (const line of lines) {
    if (!line) continue;
    const { response, error } = JSON.parse(line);
    if (error) { /* 处理错误 */ }
    if (response) { /* 处理增量片段 */ }
  }
}
```

## 6. 文档管理
### 6.1 上传文件
- 方法/路径：`POST /documents/upload`
- Content-Type：`multipart/form-data`
- 表单字段：
  - `file`: 单文件；如需多文件可多次调用或自行扩展
- 成功响应（`InsertResponse`）：
```json
{
  "status": "success",
  "message": "File 'xxx' uploaded successfully. Processing will continue in background.",
  "track_id": "upload_..."
}
```
- 其他：可能返回 `duplicated` 状态，或抛错

示例（curl）：
```bash
curl -X POST "http://localhost:9621/documents/upload" \
  -F "file=@/path/to/file.pdf"
```

### 6.2 文本入库
- 单条文本：`POST /documents/text`
  - 请求体：`{ "text": "内容", "file_source": "可选" }`
- 多条文本：`POST /documents/texts`
  - 请求体：`{ "texts": ["内容1","内容2"], "file_sources": ["可选1","可选2"] }`
- 响应：`InsertResponse`（含 `status`, `message`, `track_id`）

### 6.3 文档状态与流水线
- 获取文档分组状态：`GET /documents`
  - 返回：按状态分组的复杂对象（并非简单数组）。
- 获取流水线状态：`GET /documents/pipeline_status`
  - 返回：`busy`, `job_name`, `history_messages`, `job_start`, `update_status` 等。

### 6.4 删除/清空
- 清空所有文档：`DELETE /documents`
  - 返回：`ClearDocumentsResponse`（`status` 为 `success`/`partial_success`/`fail`）。
- 按 ID 删除文档：`DELETE /documents/delete_document`
  - 请求体：
```json
{
  "doc_ids": ["doc-id-1", "doc-id-2"],
  "delete_file": false
}
```
  - 返回：`{ status: "deletion_started" | "busy" | "not_allowed", message: string, doc_id?: string }`

## 7. 知识图谱
- 获取标签列表：`GET /graph/label/list`
- 获取子图：`GET /graphs?label=XXX&max_depth=3&max_nodes=1000`
- 判断实体是否存在：`GET /graph/entity/exists?name=实体名`
- 编辑实体：`POST /graph/entity/edit`
  - 请求体：`{ entity_name: string, updated_data: object, allow_rename?: boolean }`
- 编辑关系：`POST /graph/relation/edit`
  - 请求体：`{ source_id: string, target_id: string, updated_data: object }`

## 8. 与 WebUI 类型的差异说明
- WebUI 中的 TypeScript 类型对部分响应做了简化（例如 `HealthResponse`、`/documents` 返回值）。
- 对接微服务时应以后端真实返回结构为准，尤其是：
  - 流式查询请使用 `/query/stream`（NDJSON），不要使用 SSE 头访问 `/query`。
  - `/documents` 为分组对象而非简单数组。

## 9. 最简整合示例
- 非流式问答（axios）：
```ts
const resp = await axios.post('http://localhost:9621/query', {
  query: '介绍一下项目架构',
  mode: 'mix',
  top_k: 10
});
console.log(resp.data.response);
```

- 流式问答（NDJSON 行读取）：
```ts
const res = await fetch('http://localhost:9621/query/stream', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ query: '介绍一下项目架构', mode: 'mix' })
});
for await (const chunk of res.body as any) {
  const lines = chunk.toString().trim().split('\n');
  for (const line of lines) {
    if (!line) continue;
    const { response, error } = JSON.parse(line);
    if (error) { /* 处理错误 */ }
    if (response) { /* 处理增量片段 */ }
  }
}
```

- 上传文件（curl）：
```bash
curl -X POST "http://localhost:9621/documents/upload" \
  -F "file=@/path/to/file.pdf"
```

---
如需，我可以为你的新项目提供最小化 SDK（TypeScript/Go/Python）以统一封装上述调用。