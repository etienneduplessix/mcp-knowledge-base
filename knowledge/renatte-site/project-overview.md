# 项目概览 — renatte-site

## 项目名称
renatte-site（南京瑞纳特智能技术有限公司官方网站）

## 定位
面向产业园区管理者与企业用户的**智慧园区软件平台展示官网**，提供解决方案展示、案例介绍与 RenatteMD Markdown 编辑器下载分发。

## 核心能力
- **双语国际化（i18n v2.0）**：中英文自动检测 + 手动切换 + localStorage 偏好持久化；翻译数据与逻辑分离（`locales/zh.js` / `en.js`），`data-i18n` 属性统一驱动 DOM 更新，`scripts/check-i18n.js` 自动校验 key 完整性
- **管理后台**：登录认证（SVG 验证码 + 密码 + 邮箱 OTP）、数据概览看板、数据详情弹窗、文件上传/下载管理、数据清理
- **数据分析存储（analytics-db v2.1.0）**：SQLite 存储（pageviews/downloads/audit_logs/admin_config 四表），失败降级 JSON
- **RenatteMD 编辑器下载**：分平台分发包、版本管理、下载计数

## 技术栈
- **前端**：HTML5 + Tailwind CSS (CDN) + Vanilla JS（无框架、无构建步骤）
- **后端**：Node.js (v20+) + Express 4
- **数据库**：better-sqlite3 + SQLite（WAL 模式），JSON 降级兜底
- **部署**：腾讯云 Ubuntu 24.04 + Nginx（纯反向代理）+ PM2 + Let's Encrypt (Certbot)

## 版本
- 当前版本：2.0.0（package.json name: `webstie`）
- 许可证：AFL-3.0
- 官网：https://www.renatte.com

## 目录结构
| 路径 | 用途 |
|------|------|
| `index.html` | 首页（单页），SEO meta、各版块 HTML |
| `admin/index.html` / `admin/login.html` | 管理后台看板 / 登录页 |
| `css/style.css` / `css/i18n.css` | 全局样式 / 语言切换按钮样式 |
| `js/i18n.js` | 国际化引擎（逻辑层，214 行） |
| `js/script.js` | 页面交互脚本 |
| `locales/zh.js` / `locales/en.js` | 翻译数据（全局变量 `LOCALE_zh` / `LOCALE_en`） |
| `server/server.js` | Express 应用入口（路由/中间件/安全/认证） |
| `server/database.js` | SQLite 初始化、迁移、CRUD、统计查询（降级 JSON） |
| `scripts/check-i18n.js` | i18n key 完整性校验 |
| `scripts/tools/*.py` | 部署 / SSL / 数据修复等运维脚本（Python） |
| `specs/` | 规范文档（业务/技术/编码/模块设计） |
| `docs/SERVER-SPEC.md`（知识库 `docs/renatte-site/`） | 服务器配置规格书 |
| `data/` | 运行时数据：`analytics.db`（主）、`analytics/`（JSON 降级）、`admin-config.json`、`uploads/` |

## 快速启动
```bash
npm install
node server/server.js   # 或 npm run dev，默认端口 3000
```

## 验证标准
- `node scripts/check-i18n.js` 无遗漏（exit 0）
- 语言切换后所有可见文本正确更新
- 管理后台登录 → 看板 → 数据详情全链路可用
