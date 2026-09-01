# 架构说明 — renatte-site

## 总体架构

```
浏览器 (index.html + i18n.js + CSS)
        │  HTTP/HTTPS
        ▼
Nginx (:80 / :443)   —— SSL 终止 · 安全头 · 速率限制 · proxy_pass → :3000
        ▼
Node.js Express (:3000)
  ├── 静态文件 (express.static)：HTML/CSS/JS
  ├── API 路由：管理后台认证 / 文件上传 / 分析追踪 / 下载
  └── 中间件栈：CSP/XFO 安全头 · CORS · cookie-parser · CSRF
        │
        ▼
better-sqlite3 (data/analytics.db, WAL 模式)  ← 失败降级 JSON 文件
```

## 前端架构

- 单页静态站，无构建工具，Tailwind CSS 走 CDN
- `js/i18n.js` 国际化引擎（逻辑层）：
  - `init()` 语言检测 + 加载 `LOCALE_zh`/`LOCALE_en` + 渲染
  - `setLanguage()` 切换语言（写 localStorage）
  - `updateDataI18n()` 扫描 `[data-i18n]` 更新文本（主力机制）
  - `t(path)` 按点分隔路径取翻译文本
  - `resolvePath()` 递归路径解析
- 翻译数据在 `locales/zh.js` / `en.js`，经 `<script>` 标签加载为全局变量
- 设计原则：新增内容只加 `data-i18n` 属性 + 两侧翻译 key，无需改 JS

## 后端架构（server/server.js）

Express 应用，端口 `process.env.PORT || 3000`，安全中间件栈 + API 路由：

| 区块 | 职责 |
|------|------|
| 安全中间件 | 自定义安全头（CSP/XFO）、CORS（白名单）、body-parser、cookie-parser |
| 验证码 | SVG 图形验证码（`/api/captcha`），5min 过期，最多 3 次尝试 |
| CSRF | Double-Submit Cookie，4h 过期（`/api/csrf-token`） |
| 登录限流 | 内存 Map，5 次失败锁定 15 分钟（`/api/admin/login`） |
| OTP | 6 位邮箱验证码，5min 过期，60s 冷却（`/api/admin/send-otp`） |
| 会话 | 内存 Map，24h 过期，`x-admin-token` header（authMiddleware） |
| 分析 | pageview / download 埋点写入 SQLite |
| 文件上传 | multer，MIME/扩展名白名单（exe/deb/appimage/dmg/msix/zip/msi） |

## 数据库架构（server/database.js）

四张表 + 自动迁移 + 降级：

| 表 | 用途 | 关键索引 |
|----|------|----------|
| `pageviews` | 访问埋点（path/referrer/user_agent/timestamp） | `idx_pv_timestamp` |
| `downloads` | 下载埋点（filename/version/platform/timestamp） | `idx_dl_timestamp` |
| `audit_logs` | 审计日志（event/ip/details/timestamp） | `idx_audit_timestamp` |
| `admin_config` | 管理员配置（key/value，含保留天数） | PRIMARY KEY(key) |

- 启动时 `initDatabase()` 建表 + `migrateFromJSON()` 幂等迁移旧 JSON 数据
- 聚合统计用 SQL（today/week/month/total + 30 天每日分组）
- 清理策略：pageviews 90 天 / downloads 365 天 / audit_logs 90 天，启动 + 每 24h 自动清理，后台可手动触发
- 降级：SQLite 初始化失败时回退 JSON 文件读写（导出 `isReady` 标志）

## 安全架构

| 维度 | 方案 |
|------|------|
| 密码存储 | PBKDF2-SHA512，自定义迭代次数 |
| 会话 | 内存 Map，24h 过期，`x-admin-token` header |
| CSRF | Double-Submit Cookie，4h 过期 |
| 验证码 | SVG 图形验证码，5min 过期 |
| OTP | 6 位邮箱验证码，5min 过期 |
| 速率限制 | Nginx 限制登录/OTP/验证码接口 |
| SSL | TLSv1.2 + TLSv1.3，Let's Encrypt |
| 安全头 | HSTS、XFO、CSP、XSS-Protection 等 |

## 部署架构

- 腾讯云轻量应用服务器（Ubuntu 24.04 LTS），单节点无集群
- Nginx **纯反向代理**（铁律：不直接返回静态文件，统一 `proxy_pass` 到 :3000）
- PM2 守护 Node 进程（`pm2 restart server`）
- 部署：SCP 上传 → 替换工作目录 `/home/ubuntu/renatte-website/` → PM2 重启
