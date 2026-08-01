# MCP 工具参考(12 个工具)

所有工具注册于 `MCPServer("knowledge-base")`。参数均有类型注解,由 MCP SDK 自动生成 JSON Schema。

## 读取类(5 个)

### kb_read_file(file_path: str) -> str
读取知识库文件。
- `file_path`: 相对或绝对路径
- 返回: 文件头信息(名称/路径/大小) + 内容(JSON 文件自动解析展示)

### kb_search(query: str, file_pattern: str | None = None) -> str
全文搜索。
- `query`: 要搜索的文本
- `file_pattern`: 可选 glob 过滤(如 `*.md`、`*.json`)
- 返回: 匹配文件列表、每文件匹配数、匹配行上下文

### kb_list_files(extension: str | None = None) -> str
列出知识库文件。
- `extension`: 可选扩展名过滤(如 `.md`、`.json`)
- 返回: 文件名称、扩展名、路径、大小

### kb_get_file_info(file_path: str) -> str
获取文件元数据。
- 返回: 路径、扩展名、大小、类型(JSON 有效/无效、文本)

### kb_query_json(file_path: str, expression: str | None = None) -> str
JSONPath 查询。
- `expression`: JSONPath 表达式(缺省返回完整 JSON)
- 返回: 匹配结果或错误信息

## 写入类(5 个)

### kb_create_file(file_path: str, content: str) -> str
创建新文件(路径相对知识库根)。
- 返回: 名称、路径、大小、成功消息

### kb_write_file(file_path: str, content: str) -> str
覆盖写入整个文件。
- 返回: 名称、路径、大小、成功消息

### kb_edit_file(file_path: str, old_text: str, new_text: str) -> str
查找替换编辑。
- `old_text` / `new_text`: 原文与替换文本
- 返回: 替换次数、成功消息

### kb_append_file(file_path: str, content: str) -> str
追加内容到文件末尾。
- 返回: 新大小、成功消息

### kb_delete_file(file_path: str) -> str
删除文件。
- 返回: 成功消息

### kb_restore_backup(file_path: str) -> str
从 `.bak` 备份恢复文件。
- 返回: 成功消息

## 媒体类(1 个)

### kb_process_media(file_path: str, contact_name: str | None = None) -> str
处理媒体文件。
- `file_path`: 媒体文件路径
- `contact_name`: 可选联系人,用于关联媒体记录
- 返回: 类型、提取文本/转录(按语言)、记录 JSON 路径(`media/` 目录)

## 内建 Prompts(2 个)
- `kb_help`: 获取工具使用帮助
- `kb_analyze_file(file_path)`: 分析知识库文件并提供见解

## 统一行为
- 所有工具经 `_safe_tool` 包装:异常转为 `Error: <message>` 文本返回,不崩溃
- 返回格式均为 Markdown,便于 Agent 直接阅读
