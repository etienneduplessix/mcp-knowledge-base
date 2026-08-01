# 项目概览

## 项目名称
MCP Knowledge Base Server(mcp-knowledge-base)

## 定位
一个基于 Model Context Protocol (MCP) 的**知识库服务器**,为编码 Agent 提供 Markdown / JSON 文件的读取、搜索、查询**和编辑**能力。

## 核心能力
- **读取**:读取 Markdown / JSON 文件内容,JSON 自动解析
- **全文搜索**:跨所有索引文件全文搜索,支持 glob 模式过滤(`*.md`、`*.json`)
- **JSONPath 查询**:对 JSON 文件执行 JSONPath 表达式查询
- **写入**:创建、覆盖、查找替换编辑、追加、删除文件
- **安全机制**:自动备份(`<name>.<ext>.bak`)、原子写入(`.tmp` + `os.replace`)、可从备份恢复
- **媒体处理**:`kb_process_media` 处理媒体文件(提取文本/转录,记录 JSON 到 `media/` 目录)

## 技术栈
- **MCP SDK 2.0.0**(`mcp` 包,高层 `MCPServer` API)
- Python 3.10+(当前环境 3.13.7)
- pydantic v2、click(CLI)、jsonpath-ng(JSONPath 查询)

## 目录结构
| 路径 | 用途 |
|---|---|
| `mcp_kb_server.py` | 核心 MCP 服务器(唯一入口) |
| `media_processor.py` | 媒体处理模块(被安全导入,有 `main` 保护) |
| `knowledge/` | 项目知识库目录(索引根之一) |
| `docs/` | 文档目录(索引根之一) |
| `config/` | 配置文件与 MCP 客户端模板 |
| `test_kb.py` | 测试脚本(10 项) |
| `setup.py` / `install.sh` | 安装配置向导 |
| `Dockerfile` / `docker-compose*.yml` | Docker 部署 |

## 快速启动
```bash
pip install -r requirements.txt
python test_kb.py        # 运行测试(可选)
python mcp_kb_server.py  # 启动 stdio 服务器
python mcp_kb_server.py -t sse --port 8000  # SSE 传输
```

## 验证标准
- `python test_kb.py` 10 项测试全过
- 端到端验证用 `mcp.client.stdio` 连接
