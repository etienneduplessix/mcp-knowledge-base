# 安装与配置指南

## 安装依赖

```bash
pip install -r requirements.txt
# 或开发模式
pip install -e ".[dev]"
```

## 知识库路径配置(三种方式)

### 1. 命令行参数(手动启动)
```bash
python mcp_kb_server.py -p ./knowledge -p ./docs -p ./config
```

### 2. 环境变量 KB_PATHS(推荐,MCP 客户端配置)
```bash
set KB_PATHS=./knowledge,./docs,./config
set KB_EXTENSIONS=.md,.json
set KB_MAX_SIZE_MB=10
python mcp_kb_server.py
```

### 3. 默认路径
无任何配置时:`./knowledge` + `./docs`(启动时会警告不存在的路径,不报错)

## 客户端接入模板(config/ 目录)

| 客户端 | 模板文件 | 说明 |
|---|---|---|
| VS Code | `config/vscode-mcp.json.template` | 项目级 `.vscode/mcp.json` |
| Claude Desktop | `config/claude-desktop-config.json.template` | 全局配置 |
| Claude Code | `config/claude-code-mcp.json.template` | `~/.claude.json` |
| Cursor | `config/cursor-mcp.json.template` | 项目级 `.cursor/mcp.json` |
| OpenCode | `config/opencode.json.template` | `~/.config/opencode/opencode.json` |

### 关键配置要点
- `command`: Python 可执行文件路径
- `args`: `["<绝对路径>/mcp_kb_server.py"]`
- `env.KB_PATHS`: 知识库根路径,逗号分隔,建议用绝对路径
- 本项目建议:`KB_PATHS` 指向 `knowledge`、`docs`、`config` 三个目录

### ⚠️ 用户级 mcp.json 不要用 `${workspaceFolder}`

`${workspaceFolder}` 只在**已打开文件夹**的窗口中才能解析。若把它写在**用户级** `mcp.json`(`%APPDATA%\Code\User\mcp.json`),那么在无文件夹的窗口启动该服务器会直接失败:

```
CodeExpectedError: 无法解析变量 workspaceFolder。请打开一个文件夹。
```

推荐做法:
- **用户级 `mcp.json`**:只写**绝对路径**,保证任意窗口(含无文件夹窗口)都能启动。
- **项目级 `.vscode/mcp.json`**:需要检索当前项目自己的 `specs/knowledge/docs/config` 时,把 `${workspaceFolder}/...` 写在项目级配置里 —— 它只在打开该文件夹时加载,不存在解析失败问题。

### 示例(Claude Desktop 风格)
```json
{
  "mcpServers": {
    "knowledge-base": {
      "command": "python",
      "args": ["D:/work/mcp-knowledge-base/mcp_kb_server.py"],
      "env": {
        "KB_PATHS": "D:/work/mcp-knowledge-base/knowledge,D:/work/mcp-knowledge-base/docs,D:/work/mcp-knowledge-base/config"
      }
    }
  }
}
```

## Docker 部署
```bash
make docker-build   # 构建镜像
make docker-run     # docker compose 运行
make docker-test    # 容器内测试
```
容器内挂载知识库目录为只读(`:ro`)时,写入类工具不可用,仅支持读取/搜索/查询。

## 项目内 mcp-config.json
```json
{
  "knowledge_base_paths": ["./knowledge", "./docs", "./config"],
  "file_extensions": [".md", ".json"],
  "max_file_size_mb": 10
}
```

## 启动传输模式
- `stdio`(默认):本地进程间通信
- `sse`:`python mcp_kb_server.py -t sse --port 8000`,暴露 `GET /sse` 与 `POST /messages/`
