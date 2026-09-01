# 开发计划 — i18n 国际化优化

> 基于 specs/04-module-i18n.md 的实施方案
> 预估工时：3-5 天（渐进式，可阶段性上线）

---

## 阶段划分

### 🎯 阶段一：翻译数据拆分（1天）

**目标：** 将翻译数据从 `js/i18n.js` 分离为独立 JSON 文件，消除数据与逻辑的耦合。

| 任务 | 产出 | 说明 |
|------|------|------|
| 1.1 创建 `locales/` 目录 | `locales/zh.json` | 从 `translations.zh` 提取 |
| 1.2 创建英文翻译文件 | `locales/en.json` | 从 `translations.en` 提取 |
| 1.3 将 JSON 嵌入 HTML | `index.html` 添加 `<script src="locales/zh.json">` | 通过全局变量挂载 |
| 1.4 改造 `i18n.js` 加载逻辑 | `js/i18n.js` 更新 | 从 JSON 全局变量读取翻译 |
| 1.5 验证 | 语言切换功能正常 | 与原行为一致 |

**验收标准：** 所有页面文本切换正确，与优化前行为 100% 一致。

---

### 🎯 阶段二：统一 `data-i18n` 机制（2天）

**目标：** 消除 `updateContent()` 中的直接 DOM 操作，全部改用 `data-i18n` 属性。

| 任务 | 产出 | 说明 |
|------|------|------|
| 2.1 增强 `updateDataI18n()` | 支持递归路径解析 | 实现 `resolvePath()` |
| 2.2 Hero 区块迁移 | `index.html` + 删除对应 JS 代码 | 约 30 个元素 |
| 2.3 Stats 区块迁移 | `index.html` + 删除对应 JS 代码 | 4 个元素 |
| 2.4 Products 区块迁移 | `index.html` + 删除对应 JS 代码 | 约 30 个元素 |
| 2.5 Features 区块迁移 | `index.html` + 删除对应 JS 代码 | 约 10 个元素 |
| 2.6 Cases 区块迁移 | `index.html` + 删除对应 JS 代码 | 约 20 个元素 |
| 2.7 About 区块迁移 | `index.html` + 删除对应 JS 代码 | 约 25 个元素 |
| 2.8 Contact 区块迁移 | `index.html` + 删除对应 JS 代码 | 5 个元素 |
| 2.9 Footer 区块迁移 | `index.html` + 删除对应 JS 代码 | 约 15 个元素 |
| 2.10 Download 区块对齐 | `index.html` 统一格式 | 约 20 个元素 |
| 2.11 删除 `updateContent()` | `js/i18n.js` 清理 | 删除约 400 行冗余代码 |

**验收标准：** `updateContent()` 完全删除，所有翻译仅由 `data-i18n` 驱动。

---

### 🎯 阶段三：校验脚本（1天）

**目标：** 开发自动化校验工具，防止遗漏翻译 key。

| 任务 | 产出 | 说明 |
|------|------|------|
| 3.1 编写 `scripts/check-i18n.js` | 脚本文件 | HTML 提取 → JSON 比对 |
| 3.2 HTML key 提取函数 | 正则提取 `data-i18n` 属性值 | 支持去重、排序 |
| 3.3 JSON key 遍历函数 | 递归获取所有叶子 key | 支持嵌套结构 |
| 3.4 差异报告 | 缺失 key / 冗余 key / 不对称 | 带颜色输出（chalk 可选） |
| 3.5 集成到开发流程 | `package.json` scripts | `npm run check:i18n` |

**验收标准：**
- 有遗漏时 `exit(1)` + 明确提示
- 完整时 `exit(0)` + 统计摘要
- 运行时间 < 500ms

---

### 🎯 阶段四：HTML 文本清理（0.5天）

**目标：** 清除 HTML 中的硬编码非占位文本，确保所有显示文本由 `data-i18n` 驱动。

| 任务 | 产出 | 说明 |
|------|------|------|
| 4.1 运行校验脚本 | 发现遗漏 | 迭代修复 |
| 4.2 审查所有文本节点 | 确保无遗漏 | 可视化审查 |

**验收标准：** `check-i18n.js` 静默通过，无任何遗漏。

---

## 风险与应对

| 风险 | 概率 | 影响 | 应对 |
|------|------|------|------|
| 迁移后某元素未正确更新 | 中 | 中 | 分区块迁移，每完成一个区块立即验证 |
| 包含 HTML 标签的翻译（如 footer.copyright 含 `<a>`） | 高 | 低 | `data-i18n` 支持 innerHTML 模式，用 `data-i18n-html` 区分 |
| 数组类型翻译（如 weekdays） | 中 | 低 | `data-i18n` 支持索引语法 `weekdays[0]` |

---

## 完成标准

- [ ] `updateContent()` 函数完全删除
- [ ] 所有页面文本通过 `data-i18n` 驱动
- [ ] `scripts/check-i18n.js` 静默通过
- [ ] zh/en 翻译文件结构一致，无冗余 key
- [ ] 语言切换功能完整正常
