# API Reference — 项目知识库 MCP 服务器

本文档描述 `mcp_kb_server.py` 提供的全部 MCP 工具、Prompt、CLI 命令与配置项。

> **注意：** 本服务器通过 **Model Context Protocol (MCP)** 与编码智能体通信（stdio 传输），并非 REST API。

---

## 1. MCP 工具

服务器注册了 17 个工具，按功能分为四类。

### 1.1 知识库读取（只读）

| 工具 | 描述 | 必填参数 |
|------|------|---------|
| `kb_list_files` | 列出所有知识库文件，可按扩展名过滤 | `extension`（可选） |
| `kb_read_file` | 读取文件完整内容（markdown/JSON），JSON 会附带解析结果 | `file_path` |
| `kb_search` | 全文搜索（不区分大小写），返回带行上下文的匹配 | `query`、`file_pattern`（可选） |
| `kb_get_file_info` | 获取文件元数据（路径/扩展名/大小/类型） | `file_path` |
| `kb_query_json` | 用 JSONPath 查询 JSON 文件（如 `$.database.host`） | `file_path`、`expression`（可选） |

### 1.2 知识库写入（CRUD）

| 工具 | 描述 | 必填参数 |
|------|------|---------|
| `kb_create_file` | 创建新文件（已存在则报错） | `file_path`、`content` |
| `kb_write_file` | 覆写文件内容（不存在则创建） | `file_path`、`content` |
| `kb_edit_file` | 查找并替换文本（仅替换首个匹配） | `file_path`、`old_text`、`new_text` |
| `kb_append_file` | 追加内容到文件末尾（不存在则创建） | `file_path`、`content` |
| `kb_delete_file` | 删除文件 | `file_path` |

### 1.3 Spec 驱动开发（生成规范文档）

| 工具 | 描述 | 可选参数 |
|------|------|---------|
| `kb_generate_business_spec` | 生成**业务架构规范**（概述/领域模型/流程/用例/干系人/KPI） | `file_path` 保存到 specs/ |
| `kb_generate_tech_spec` | 生成**技术架构规范**（技术栈/架构/数据流/API/数据库/安全/部署） | `languages`、`frameworks`、`databases`、`file_path` |
| `kb_generate_coding_standards_spec` | 生成**编码规范**（语言约定/命名/文档/测试/Git 流程） | `language`、`file_path` |
| `kb_generate_module_design_spec` | 生成**模块详细设计**（接口/数据结构/核心逻辑/依赖/测试策略） | `module_name`（必填）、`file_path` |

### 1.4 代码反向同步（漂移检测）

| 工具 | 描述 | 必填参数 |
|------|------|---------|
| `kb_analyze_code` | 扫描分析源代码（AST 解析/类/函数/API 路由/数据模型/依赖/测试） | `source_path` |
| `kb_check_spec_drift` | 对比 spec 与实际代码，检测 missing/extra/changed 漂移 | `spec_path`、`source_path` |
| `kb_sync_spec_from_code` | 生成漂移报告，指导 spec 与代码同步 | `spec_path`、`source_path` |

---

## 2. MCP Prompts

| Prompt | 描述 |
|--------|------|
| `kb_help` | 获取知识库工具使用帮助 |
| `kb_analyze_file` | 分析指定知识库文件并提供洞察（参数：`file_path`） |

---

## 3. MCP Resources

每个知识库文件都会注册为一个资源：

- URI 格式：`kb://<绝对路径>`
- MIME 类型：`.json` → `application/json`，`.md` → `text/markdown`

---

## 4. CLI 命令

```bash
python mcp_kb_server.py [command] [options]
```

| 命令 | 描述 | 示例 |
|------|------|------|
| （无参数） | 启动 MCP 服务器（stdio） | `python mcp_kb_server.py` |
| `serve` | 启动 MCP 服务器（默认 stdio） | `python mcp_kb_server.py serve` |
| `init -d <dir> -n <name>` | 初始化项目目录（specs/knowledge/docs/config + opencode.json） | `python mcp_kb_server.py init -d . -n "MyApp"` |
| `gen-specs --name <name>` | 批量生成业务/技术/编码三份初始规范到 specs/ | `python mcp_kb_server.py gen-specs --name "MyApp"` |
| `registry <action>` | 管理本地 MCP Server 注册中心（list/show/add/remove/rebuild/init/path） | `python mcp_kb_server.py registry list` |

> 通过 `pip install -e .` 安装后，也可直接使用 `kb` / `kb-serve` 命令。

---

## 5. 环境变量配置

| 变量 | 默认值 | 描述 |
|------|--------|------|
| `KB_PATHS` | `./specs,./knowledge,./docs,./config` | 知识库根目录列表（逗号分隔） |
| `KB_EXTENSIONS` | `.md,.json` | 允许的文件扩展名 |
| `KB_MAX_SIZE_MB` | `10` | 单文件大小上限（MB） |

---

## 6. 错误处理

工具调用失败时返回 `Error: <message>` 文本，常见错误：

- `Access denied: <path>` — 路径超出配置的知识库目录
- `Invalid or inaccessible file: <path>` — 文件不存在、扩展名不受支持或超出大小限制
- `File already exists: <path>` — 创建时目标已存在
- `Text to replace not found in file: <text>` — 编辑时未找到待替换文本
- `Invalid JSONPath expression: <expr>` — JSONPath 表达式语法错误

---

## 7. 向后兼容

旧入口 `python mcp_kb_server.py --path <dir> --transport stdio` 仍受支持，但已标记为 **DEPRECATED**，建议改用 `serve` 命令。
