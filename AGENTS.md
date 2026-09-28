# AGENTS.md — mcp-knowledge-base

基于 mcp SDK 2.x 的自定义 MCP 知识库服务器：对 markdown/JSON 知识库文件提供读写、搜索、JSONPath 查询等能力（共 19 个工具）。

## 先读这些文档

- `knowledge/development-guide.md` — **修改 `mcp_kb_server.py` 前必读**：mcp 2.x 高层 API（`@server.add_tool` 纯装饰器）与 pydantic v2 的关键陷阱
- `knowledge/architecture.md` — 架构说明（KnowledgeBase 类、索引缓存、原子写入/备份）
- `knowledge/tools-reference.md` — 19 个工具参考
- `knowledge/setup-and-config.md` — 安装与配置（stdio / SSE 两种传输）
- `specs/` — 需求与技术规格（spec 驱动开发：planned → implementing → implemented → verified）

## 构建与测试

```bash
pip install -e ".[dev]"   # 安装含 dev 依赖（pytest/black/ruff）
python test_kb.py         # 单元测试
python test_mcp_e2e.py    # 端到端 stdio 测试
ruff check .              # lint：E/F/W/I，line-length 100
```

## Git 工作流（硬性前置步骤）

1. **修改任何代码前先 `git pull`**：若本地有未提交改动，先提醒用户 commit 或 stash。
2. **提醒建立 feature 分支**：不在 feature 分支（如在 `main`/`master`/`develop`）时，必须先提醒用户创建新分支（如 `git checkout -b feature/<描述>`），征得确认后再改代码；禁止在主干分支直接修改。
3. **修改完成后**：提醒用户审查提交（commit）、推送（push）及创建 Pull Request。

> 与用户级全局规则 `git-workflow.instructions.md` 保持一致。
