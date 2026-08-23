# 开发与维护指南

## 测试
```bash
python test_kb.py          # 10 项测试
python -m pytest tests/    # 或 pytest
```

## 开发经验(踩坑记录)

### 1. mcp SDK 2.x API 变化(最重要)
- 2.x **移除了低层装饰器 API**,必须用 `MCPServer` 高层 API
- `@server.add_tool` 是**纯装饰器**:`name` 取函数名,`description` 取 docstring
- 工厂式 `add_tool(name=..., fn=...)` 会报 **missing 'fn'** 错误
- 新增工具时:定义普通函数 + 完整 docstring + 类型注解,然后 `@server.add_tool @_safe_tool` 即可

### 2. pydantic v2
- `init.serverInfo` → `init.server_info`(驼峰→下划线)

### 3. 路径解析(Bug 修复记录)
- 原 `_resolve_kb_path` 把相对路径直接按 KB 根拼接,导致 read/query 失败
- 已修复:先按 cwd 解析,失败再回退 KB 根
- **修改路径逻辑时务必回归测试 read / query / edit 三类操作**

### 4. 缓存一致性
- `_file_cache` 以 mtime/size 做失效判断
- 删除文件后必须调用 `_invalidate_cache`,否则残留脏缓存

### 5. 写入安全
- 写操作前自动备份 `<name>.<ext>.bak`
- 原子写入:`.tmp` + `os.replace`,避免并发/中断产生半写文件

### 6. 媒体处理
- `media_processor.py` 通过安全导入接入(有 `if __name__ == "__main__"` 保护)
- 媒体记录保存为 `media/<name>.json`

## 新增知识库文档的建议结构
1. `project-overview.md` — 项目定位与概览
2. `architecture.md` — 架构与组件
3. `tools-reference.md` — 工具/API 参考
4. `setup-and-config.md` — 安装配置
5. `development-guide.md` — 开发经验

## 版本记录
- **1.0.0**:基础读写 + 搜索 + JSON 查询
- 2026-08-01 架构优化:mcp 2.0.0 迁移、路径解析修复、媒体处理集成、10 项测试全过
