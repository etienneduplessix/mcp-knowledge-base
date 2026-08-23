# 项目编码规范 — Project Coding Standards

> 适用于 mcp-knowledge-base（项目知识库）仓库。工具配置见 `pyproject.toml`。

## 1. 语言与版本

- **Python >= 3.10**
- 使用 `from __future__ import annotations`（如适用）与现代类型注解语法（`X | None`）
- 类型提示必须覆盖函数签名与数据结构字段

## 2. 代码风格（black）

- 行宽限制：**100 字符**
- 使用 black 默认格式化，配置：`[tool.black] line-length = 100`
- 格式化命令：`make fmt` 或 `black .`

## 3. 命名约定

- 类：PascalCase（如 `KnowledgeBaseConfig`）
- 函数/方法：snake_case（如 `scan_files`）
- 常量：UPPER_CASE（如 `MAX_SIZE`）
- 私有成员：单下划线前缀（如 `_is_path_allowed`）

## 4. 代码检查（ruff）

- 启用规则：`E`（pycodestyle）、`F`（pyflakes）、`W`（warning）、`I`（isort）
- 检查命令：`make lint` 或 `ruff check .`

## 5. 文档

- 所有模块必须包含模块级 docstring（描述模块用途）
- 公开函数与类必须有 docstring
- 文档注释使用中文或英文均可，但同一文件内保持一致

## 6. 错误处理

- 使用具体异常类型（`ValueError`、`KeyError` 等），避免裸 `except`
- 路径/权限类错误抛出 `ValueError` 并带清晰的中文/英文信息
- MCP 工具层用 `try/except Exception` 兜底并返回 `Error: ...` 文本

## 7. 测试（pytest）

- 使用 pytest + pytest-asyncio
- 测试命令：`python test_kb.py` 或 `make test`
- 新增功能需补充测试用例（知识库读写、搜索、JSONPath 查询、spec 生成、代码分析）
- Windows 下运行测试需先设置 `$env:PYTHONIOENCODING='utf-8'`

## 8. Git 工作流

- 功能分支从 `main` 创建
- 使用 conventional commits 风格：`feat:` / `fix:` / `docs:` / `refactor:` / `test:`
- 合并前需代码审查
- 代码与 spec 文档同步提交（Spec 驱动开发工作流）
