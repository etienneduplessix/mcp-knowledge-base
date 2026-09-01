# 编码规范

> **项目：** renatte-site（瑞纳特官网）
> **语言：** JavaScript / HTML5 / CSS3
> **版本：** 1.0.0
> **作者：** 南京瑞纳特智能技术有限公司
> **创建时间：** 2026-07-08

---

## 1. 语言约定

### 1.1 版本

- **JavaScript：** ES6+（`const`/`let`、箭头函数、模板字符串、解构赋值）
- **HTML5：** 语义化标签（`section`、`article`、`nav`、`header`、`footer`）
- **CSS：** 现代 CSS（自定义属性、`flex`/`grid`、渐变）

### 1.2 代码风格

| 规则 | 值 |
|------|-----|
| 缩进 | 2 空格 |
| 行尾 | LF |
| 引号 | 单引号（JS）、双引号（HTML） |
| 行尾分号 | 始终加分号 |
| 编码 | UTF-8（无 BOM） |

### 1.3 类型

- 不使用 TypeScript，通过 JSDoc 注释标注关键函数参数类型
- 示例：
  ```javascript
  /** @param {string} lang - 'zh' | 'en' */
  function setLanguage(lang) { ... }
  ```

---

## 2. 命名规范

| 类别 | 规范 | 示例 |
|------|------|------|
| 变量 | lowerCamelCase | `currentLang` |
| 常量 | UPPER_SNAKE_CASE | `SUPPORTED_LANGS` |
| 函数 | lowerCamelCase | `updateContent()` |
| 方法（对象属性） | lowerCamelCase | `i18n.setLanguage()` |
| 全局对象 | lowerCamelCase | `i18n` |
| CSS 类名 | kebab-case | `.lang-switcher` |
| CSS ID | kebab-case | `#lang-switcher` |
| HTML `data-` 属性 | kebab-case | `data-i18n` |
| 文件名 | kebab-case | `i18n.js` |

---

## 3. 项目结构

```
renatte-site/
├── index.html                      # 首页（单页）
├── renattemd-index-redirect.html   # RenatteMD 下载重定向页
├── admin/                          # 管理后台
│   ├── index.html                  # 数据概览仪表盘（含详情弹窗）
│   └── login.html                  # 登录页（验证码 + 密码 + OTP）
├── css/
│   ├── style.css                   # 全局样式
│   └── i18n.css                    # 语言切换按钮样式
├── js/
│   └── i18n.js                     # 国际化引擎（逻辑层，翻译数据已分离）
├── locales/                        # 翻译数据文件（与逻辑分离）
│   ├── zh.js                       # 中文翻译（导出全局 LOCALE_zh）
│   └── en.js                       # 英文翻译（导出全局 LOCALE_en）
├── server/
│   ├── server.js                   # Express 服务器（路由/中间件/安全）
│   └── database.js                 # SQLite 数据库（建表/迁移/查询，降级 JSON）
├── scripts/                        # 工具脚本
│   ├── check-i18n.js               # 国际化 key 校验脚本
│   └── tools/                      # 部署/SSL/数据修复运维脚本（Python）
├── config/                         # 配置
├── data/                           # 运行时数据（服务端）
│   ├── admin-config.json           # 管理员配置（降级文件）
│   ├── analytics.db                # SQLite 数据库（主存储）
│   └── analytics/                  # JSON 降级存储
├── docs/                           # 运维文档
├── specs/                          # 规范文档
│   ├── README.md
│   ├── 01-business.md
│   ├── 02-tech.md
│   ├── 03-coding.md
│   └── 04-module-i18n.md
├── docs/                       # 运维文档
│   └── SERVER-SPEC.md
└── data/                       # 运行时数据（服务端）
    ├── admin-config.json
    ├── analytics/
    └── audit-log.json
```

---

## 4. 国际化代码规范

### 4.1 `data-i18n` 属性规范（优化后标准）

```html
<!-- ✅ 正确：使用 data-i18n 属性，值为点分隔的路径 -->
<h1 data-i18n="hero.title">默认中文文本</h1>
<p data-i18n="hero.desc">默认中文描述</p>

<!-- ❌ 错误：不使用 data-i18n 时 */
<!-- <h1 class="hero-title">硬编码文本</h1> -->
```

Key 路径规则：
- 格式：`section.subsection.key`
- 对应 `translations[lang].section.subsection.key`
- 不允许在 HTML 中直接写非占位文本（占位文本用默认属性值）

### 4.2 翻译数据规范

```javascript
// ✅ 正确：保持层级结构与 HTML 中的 data-i18n 路径一致
{
  hero: {
    title: '构建新一代',
    desc: '描述文字...'
  },
  "cases.cta": {
    title: '您的园区项目'  // 允许用点号作为 key
  }
}

// ❌ 错误：层级不匹配
{
  heroTitle: '构建新一代',  // HTML 中 data-i18n="hero.title" 找不到此 key
}
```

### 4.3 新增元素的步骤

1. 在 HTML 中添加元素，加上 `data-i18n="section.key"`
2. 元素内容写入默认语言（中文）文本作为 fallback
3. 在 `locales/zh.js` 和 `locales/en.js` 中添加对应 key 的翻译
4. 运行 `node scripts/check-i18n.js` 验证无遗漏

---

## 5. 错误处理

| 场景 | 处理方式 |
|------|---------|
| 翻译 key 在 zh 中存在但 en 中缺失 | 回退显示 key 名或 zh 值，console.warn |
| `data-i18n` 指向不存在的 key | 保留 HTML 默认内容，console.warn |
| 语言切换时 DOM 元素不存在 | 静默跳过（已有防御性判空） |
| 管理后台 token 过期 | 跳转到登录页 |

---

## 6. 测试要求

| 类型 | 覆盖内容 | 方式 |
|------|----------|------|
| i18n key 校验 | 所有 data-i18n 在 zh/en 中都有对应值 | `scripts/check-i18n.js` |
| 结构完整性 | translations 结构在 zh/en 间一致 | 脚本自动化 |
| 页面渲染 | 切换语言后所有可见文本正确更新 | 手动验证 |

---

## 7. Git 工作流

### 7.1 分支策略

- `master` — 生产就绪代码
- `feature/*` — 功能开发分支

### 7.2 提交信息格式

```
<type>(<scope>): <简短描述>

类型: feat / fix / refactor / docs / style / chore
scope: i18n / server / admin / seo / deploy
```

示例：
```
feat(i18n): 统一 data-i18n 替换直接 DOM 操作
fix(server): 修复上传 body size 限制不生效
```

### 7.3 提交前检查清单

- [ ] 所有新增的 HTML 文本都有 `data-i18n` 属性
- [ ] zh / en 翻译文件均已同步更新
- [ ] 运行 `node scripts/check-i18n.js` 无报错
- [ ] 管理后台页面不受影响
