# 架构说明

## 总体架构

```
MCP 客户端 (Claude/Cursor/VS Code/OpenCode)
        │  stdio 或 SSE
        ▼
create_kb_server(config) ──► MCPServer("knowledge-base")
        │
        ▼
KnowledgeBase(KnowledgeBaseConfig)
        ├── 内容索引缓存 (mtime/size 失效)
        ├── 原子写入 (.tmp + os.replace)
        └── 自动备份 (<name>.<ext>.bak)
```

## 关键组件

### 1. `KnowledgeBaseConfig`(dataclass)
- `paths: List[Path]` — 知识库根路径列表(可多个)
- `file_extensions: List[str]` — 索引扩展名,默认 `[".md", ".json"]`
- `max_file_size_mb: int` — 文件大小上限,默认 10

### 2. `KnowledgeBase` 类
- `_file_cache`:路径 → `{mtime, size, content, lines}` 缓存
- **缓存失效策略**:每次访问比较 `st_mtime` 与 `st_size`,变化则重载
- **原子写入**:先写 `.tmp` 再 `os.replace`,避免半写文件
- **自动备份**:写操作前备份原文件为 `<name>.<ext>.bak`
- `restore_from_backup()`:从 `.bak` 恢复
- `process_media()`:媒体处理,记录 JSON 到 `media/` 目录

### 3. `create_kb_server(config)` — MCP 服务器工厂
- 使用 **mcp 2.x 高层 API**:`MCPServer(name, title, description, version)`
- 静态注册 `Resource`(kb:// 协议 URI)
- 工具通过 `@server.add_tool` 纯装饰器注册(见下文重要约束)
- Prompt 通过 `Prompt.from_function` 注册

## 传输方式

| 传输 | 函数 | 用途 |
|---|---|---|
| stdio | `serve_kb_server(config)` | 本地 MCP 客户端(默认) |
| SSE | `serve_kb_server_sse(config, host, port)` | 远程访问,`GET /sse` + `POST /messages/` |

## 配置优先级(CLI 入口 `main`)
1. `--path` / `-p` 命令行参数(可多次指定)
2. `KB_PATHS` 环境变量(逗号分隔,MCP 客户端 env 配置)
3. 默认路径 `./knowledge` + `./docs`

## 重要约束(易踩坑)

### mcp 2.x 与 1.x API 差异
- **2.x 移除了低层装饰器 API**,必须用 `MCPServer` 高层 API
- `@server.add_tool` 是**纯装饰器**用法:`name` 取函数名,`description` 取 docstring
- **工厂式调用 `add_tool(name=...)` 会报 missing 'fn' 错误**

### pydantic v2 兼容
- `init.serverInfo` → 必须写成 `init.server_info`

### 路径解析
- `_resolve_kb_path` 已修复:相对路径**先按 cwd 解析**,再回退 KB 根
- 不要假设相对路径一定基于 KB 根拼接(会导致 read/query 失败)

## 安全导入
- `media_processor.py` 被 `mcp_kb_server.py` 安全导入(带 `main` 保护),不会在导入时执行副作用
