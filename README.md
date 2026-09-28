# 项目知识库 / MCP Knowledge Base Server

一个基于 **Model Context Protocol (MCP)** 的知识库服务器，为编码智能体（OpenCode / Copilot / Claude）提供**知识管理**、**Spec驱动开发**和**代码反向同步**能力。

> 中文名：**项目知识库** — OpenCode / 任意MCP客户端中直接使用此名称调用

---

## 核心能力

### 📖 知识库管理

| 工具 | 功能 |
|------|------|
| `kb_list_files` | 列出所有知识库文件 |
| `kb_read_file` | 读取文件内容 |
| `kb_search` | 全文搜索（带行上下文） |
| `kb_get_file_info` | 获取文件元数据 |
| `kb_query_json` | JSONPath 查询 JSON 文件 |
| `kb_create_file` / `kb_write_file` | 创建/覆写文件 |
| `kb_edit_file` / `kb_append_file` | 编辑/追加文件 |
| `kb_delete_file` | 删除文件 |
| `kb_restore_backup` | 从备份恢复文件 |
| `kb_process_media` | 媒体处理（图片 OCR / 音视频转录） |

### 📐 Spec 驱动开发

| 工具 | 功能 | file_path 参数 |
|------|------|---------------|
| `kb_generate_business_spec` | 生成**业务架构规范**（项目概述/领域模型/流程/用例/KPI） | 可选，保存到 specs/ |
| `kb_generate_tech_spec` | 生成**技术架构规范**（技术栈/架构/数据流/API/安全/部署） | 可选，保存到 specs/ |
| `kb_generate_coding_standards_spec` | 生成**编码规范**（语言约定/命名/文档/测试/Git） | 可选，保存到 specs/ |
| `kb_generate_module_design_spec` | 生成**模块详细设计**（接口/数据结构/算法/依赖/测试策略） | 可选，保存到 specs/ |

### 🔄 代码反向同步

| 工具 | 功能 |
|------|------|
| `kb_analyze_code` | 扫描分析源代码（AST解析/路由检测/依赖提取） |
| `kb_check_spec_drift` | 对比 spec 与实际代码，检测 missing/extra/changed 漂移 |
| `kb_sync_spec_from_code` | 生成漂移报告，指导 spec 同步更新 |

检测维度：项目名称、编程语言、类/模块、函数签名、API路由、依赖、数据模型、测试覆盖。

---

## 🚀 快速开始

### 初始化新项目（最快）

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 初始化项目目录和配置
python mcp_kb_server.py init -d . -n "你的项目名"

# 3. 批量生成初始规范文档
python mcp_kb_server.py gen-specs --name "你的项目名" --desc "项目简介" --author "你"

# 4. 启动 MCP 服务器
python mcp_kb_server.py serve

# 5. 启动 OpenCode / Copilot，用自然语言调用
# "用项目知识库的模块详细设计，模块名=UserService，file_path=specs/04-user.md"
```

### 集成到 IDE

**VS Code**（1.86+）：在 `.vscode/mcp.json` 中添加：

```json
{
  "servers": {
    "项目知识库": {
      "type": "stdio",
      "command": "python",
      "args": ["/path/to/mcp_kb_server.py"],
      "env": {
        "KB_PATHS": "${workspaceFolder}/specs,${workspaceFolder}/knowledge,${workspaceFolder}/docs",
        "KB_EXTENSIONS": ".md,.json"
      }
    }
  }
}
```

**OpenCode**：项目根目录放置 `opencode.json`（参见 `kb init` 自动生成）。

---

## 🔧 CLI 命令

安装后可通过 `python mcp_kb_server.py` 调用，`pip install -e .` 后可直接使用 `kb`：

| 命令 | 说明 |
|------|------|
| `kb init -d . -n "项目"` | 初始化项目目录结构（specs/ + opencode.json） |
| `kb gen-specs --name "项目"` | 批量生成业务/技术/编码三份初始规范 |
| `kb serve` | 启动 MCP 服务器（默认 stdio 传输） |
| `python mcp_kb_server.py` | 向后兼容，等同于 `kb serve` |

### 项目初始化结构

```
my-project/
├── specs/                     # 项目规范（与代码一起 Git 版本管理）
│   ├── .gitkeep
│   ├── README.md              # Spec 索引清单
│   ├── 01-business.md         # 业务架构规范
│   ├── 02-tech.md             # 技术架构规范
│   ├── 03-coding.md           # 编码规范
│   └── 04-module-*.md         # 模块详细设计（按需生成）
├── knowledge/                 # 知识库文件
├── docs/                      # 文档
├── config/                    # 配置文件
├── opencode.json              # MCP 服务器配置
└── .gitignore                 # 自动配置
```

---

## 🔄 Spec 驱动开发工作流

```
Phase 0: 初始化
  kb init + kb gen-specs
  └── 创建 specs/ + 生成初始规范

Phase 1: 自然语言建立 Spec
  "帮我在业务spec中补充订单履约流程" → kb_edit_file
  "根据业务spec设计用户模块" → kb_generate_module_design_spec + file_path

Phase 2: Spec 驱动开发
  "根据 specs/04-user.md 实现用户模块"
  IDE 读取 spec → 按接口定义实现 → 写测试

Phase 3: 交互式决策
  "注册接口要不要加验证码？"
  IDE 根据 spec 上下文给出建议 → 决策后更新 spec

Phase 4: 反向同步
  "检查 UserModule spec 和代码是否一致" → kb_check_spec_drift
  "全部同步" → 自动更新 spec 匹配实际代码

Phase 5: Git 提交（代码 + Spec 一起）
  git add src/ specs/
  git commit -m "feat(user): 实现用户模块，同步更新spec"
  git push
```

---

## 📦 项目结构

```
mcp-knowledge-base/
├── mcp_kb_server.py          # MCP 服务器（CLI + 所有工具）
├── spec_generator.py         # 四种规范文档生成器
├── code_analyzer.py          # 源代码分析引擎（AST/路由/依赖）
├── test_kb.py                # 测试套件（19 个测试用例）
├── setup.py                  # 交互式安装向导
├── pyproject.toml            # 包配置 + console_scripts 入口
├── requirements.txt          # 依赖
├── Makefile                  # 构建命令
├── config/                   # MCP 配置模板
│   ├── opencode.json.template
│   ├── claude-desktop-config.json.template
│   └── cursor-mcp.json.template
├── specs/                    # 项目级规范目录（.gitkeep）
├── knowledge/                # 示例知识库
├── docs/                     # 文档
└── tests/                    # 测试文件
```

---

## 🧪 测试

```bash
python test_kb.py
# 16/19 测试通过（3 个知识库路径测试因相对路径问题跳过）
```

---

## 📖 文档

- [SETUP.md](SETUP.md) — 详细安装指南
- [docs/INSTALLATION.md](docs/INSTALLATION.md) — AI 工具配置
- [OPENCODE.md](OPENCODE.md) — OpenCode 集成
- [EDITING_FEATURES.md](EDITING_FEATURES.md) — 文件编辑操作
- [DOCKER.md](DOCKER.md) — Docker 部署
- [QUICKSTART.md](QUICKSTART.md) — 快速参考
- [PATH_RESOLUTION.md](PATH_RESOLUTION.md) — 路径解析规则

---

## 📝 许可

MIT License — 详见 [LICENSE](LICENSE) 文件。
