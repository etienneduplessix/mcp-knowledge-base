# 瑞纳特官网 服务器配置规格书

> 版本: 1.1 | 更新: 2026-07-08 | 维护者: 边城浪子

---

## 1. 基础设施概览

### 1.1 服务器

| 项目 | 详情 |
|------|------|
| 服务商 | 腾讯云轻量应用服务器 |
| IP | `49.233.160.241` |
| 主机名 | `mail`（多用途服务器） |
| 系统 | Ubuntu 24.04.4 LTS, Kernel 6.8.0-71-generic |
| CPU / 内存 | Intel Xeon Gold 6148 @ 2.40GHz, **4 vCPU** / 3.6GiB (可用 ~1.4GiB) |
| 磁盘 | 69G (已用 37G / **56%**, 剩余 30G) |
| Swap | 9.9G (已用 1.8G) |
| 运行时间 | 118 天（自 2026-03-11） |
| Node.js | v20.20.2 |
| npm | 10.8.2 |
| PM2 | 7.0.1 |
| Nginx | 1.24.0 (Ubuntu) |

### 1.2 同机部署的其它服务

| 服务 | 端口 | 说明 |
|------|------|------|
| iRedMail | `:80/:443` 共享 | 邮件系统（dovecot, postfix, roundcube） |
| GoldClaw | `127.0.0.1:8000` | 股票数据分析 WebUI，`goldclaw.renatte.com` |
| MariaDB | `127.0.0.1:3306` | 数据库 |
| Redis | `127.0.0.1:6379` | 缓存 |
| Fail2ban | 后台 | 6 jails: dovecot, nginx-http-auth, postfix, pregreet, roundcube, sshd |

### 1.3 域名

| 域名 | 用途 |
|------|------|
| `www.renatte.com` | 主站 |
| `renatte.com` | 裸域名（301 重定向到 www） |
| `soft.renatte.com` | 软件下载子域 |
| `mail.renatte.com` | 邮件服务 |
| `goldclaw.renatte.com` | 股票分析工具 |

---

## 2. 服务架构

```
                          ┌─────────────────────────┐
                          │    Nginx :80 / :443      │
                          │  SSL 终止 · 安全头       │
                          │  速率限制 · 反向代理      │
                          └──────────┬──────────────┘
                                     │ proxy_pass
                                     ▼
                          ┌─────────────────────────┐
                          │  Node.js :3000 (PM2)     │
                          │  ┌─────────────────────┐ │
                          │  │ Express.js 应用      │ │
                          │  │ · 首页渲染           │ │
                          │  │ · 管理后台 API       │ │
                          │  │ · 文件管理 API       │ │
                          │  │ · 分析追踪           │ │
                          │  │ · CSRF/会话管理      │ │
                          │  │ · CSP 按路由设置     │ │
                          │  └─────────────────────┘ │
                          └─────────────────────────┘
```

### 2.1 端口清单

| 服务 | 绑定地址 | 端口 | 协议 | 说明 |
|------|----------|------|------|------|
| Nginx | `0.0.0.0` | 80 | HTTP | 仅做 301 重定向到 HTTPS |
| Nginx | `0.0.0.0` | 443 | HTTPS | SSL 终止 + 反向代理 |
| Node.js | `127.0.0.1` | 3000 | HTTP | Express，不直接对外 |
| Chromium Headless | `127.0.0.1` | 9222 | CDP | 无头浏览器调试端口 |

### 2.2 进程管理 (PM2)

| 参数 | `server` | `goldclaw` |
|------|----------|-----------|
| 模式 | cluster (instances: 1) | fork |
| 内存 | 41 MB | 692 MB |
| 重启次数 | 74 次 | 3 次 |
| 工作目录 | `/home/ubuntu/renatte-website/` | `/home/ubuntu/daily_stock_analysis/` |
| 启动脚本 | `server/server.js` | `main.py --webui --port 8000` |
| 最大内存 | 500MB (自动重启) | — |
| 开机自启 | ✅ (`pm2 startup` + `pm2 save`) | ✅ |
| 日志路径 | `/home/ubuntu/.pm2/logs/` | `/home/ubuntu/.pm2/logs/` |

---

## 3. Nginx 配置详解

> 配置文件: `/etc/nginx/sites-enabled/renatte-website`（**普通文件，非软链接**）  
> 项目模板: `/home/ubuntu/renatte-website/renatte-website-nginx.conf`  
> 配置备份: `/home/ubuntu/nginx-backups/`（**禁止放 sites-enabled/**，否则被 include 重复加载）

### 3.1 架构铁律 🔴

**Nginx 在本项目中唯一角色：纯反向代理。绝对禁止直接返回静态内容。**

- ❌ 禁止 `root`、`alias`、`try_files` 返回文件
- ❌ 禁止在 Nginx 中直接返回静态 HTML/CSS/JS
- ✅ 所有请求统一 `proxy_pass http://127.0.0.1:3000`
- ✅ Node.js 负责：会话鉴权、审计日志、CSP 设置、缓存策略、静态文件服务

> **血泪教训**：
> - (2026-05-24) `/admin/` 使用 `alias /var/www/html/admin/`，后台无需登录即可直接访问
> - (2026-07-08) `/renattemd/` 和 `/downloads/` 使用 `alias`，绕过 Node.js 直接返回文件
> - 已全部整改为 `proxy_pass`。

### 3.2 Location 匹配规则

按 Nginx 匹配优先级排列（均为 `proxy_pass http://127.0.0.1:3000`，无 `alias`/`root`）：

| 优先级 | Location | 用途 | 特殊配置 |
|--------|----------|------|----------|
| 1 | `= /` | 首页精确匹配 | 强制不缓存（proxy_hide_header Cache-Control/ETag/Last-Modified） |
| 2 | `/api/admin/login` | 登录接口 | 速率限制 5r/m, burst=3 |
| 3 | `/api/admin/send-otp` | OTP 发送 | 速率限制 3r/m, burst=2 |
| 4 | `/api/captcha` | 验证码 | 速率限制 30r/m, burst=10 |
| 5 | `/admin` | 管理后台 | 不缓存 |
| 6 | `/renattemd/` | RenatteMD 文件 | Node.js 处理缓存头 |
| 7 | `/downloads/` | 下载文件 | Node.js 处理缓存头 |
| 8 | `/` | 默认（兜底） | WebSocket 升级支持 |

### 3.3 速率限制

| 区域 | 键 | 速率 | 突发 | 适用接口 |
|------|-----|------|------|----------|
| `login` | `$binary_remote_addr` | 5 r/m | 3 | `/api/admin/login` |
| `captcha` | `$binary_remote_addr` | 30 r/m | 10 | `/api/captcha` |
| `otp` | `$binary_remote_addr` | 3 r/m | 2 | `/api/admin/send-otp` |

### 3.4 安全响应头

| Header | 值 |
|--------|-----|
| `Strict-Transport-Security` | `max-age=31536000; includeSubDomains` |
| `X-Content-Type-Options` | `nosniff` |
| `X-Frame-Options` | `DENY` |
| `X-XSS-Protection` | `1; mode=block` |
| `Referrer-Policy` | `strict-origin-when-cross-origin` |
| `Permissions-Policy` | `camera=(), microphone=(), geolocation=()` |
| `Content-Security-Policy` | 见 3.4.1 |

#### 3.4.1 CSP 策略

```
default-src 'self';
script-src 'self' 'unsafe-inline' 'unsafe-eval' https://busuanzi.ibruce.info;
style-src 'self' 'unsafe-inline';
img-src 'self' data: blob: https:;
font-src 'self' data:;
connect-src 'self' https://busuanzi.ibruce.info;
frame-ancestors 'none';
```

> 注意：管理后台的 CSP 由 Node.js 中间件按路由单独设置（更严格）。

### 3.5 SSL / TLS

| 项目 | 详情 |
|------|------|
| 证书 | Let's Encrypt (Certbot) |
| 路径 | `/etc/letsencrypt/live/www.renatte.com-0001/` |
| 到期 | **2026-09-04**（还有 58 天） |
| 协议 | TLSv1.2, TLSv1.3 |
| 续期 | `certbot renew`（建议设置 cron） |

### 3.6 其它 SSL 证书

| 证书名 | 域名 | 到期 |
|--------|------|------|
| `goldclaw.renatte.com` | goldclaw.renatte.com | 2026-08-28 |
| `mail.renatte.com` | mail.renatte.com | 2026-09-03 |

`www.renatte.com-0001` 同时覆盖 `mail.renatte.com`、`renatte.com`、`soft.renatte.com`。

### 3.7 其他 Nginx 配置

| 配置 | 值 | 说明 |
|------|-----|------|
| `server_tokens` | `off` | 隐藏 Nginx 版本号 |
| `client_max_body_size` | `500m` | 上传限制（server 级别） |
| `server_name` | `www.renatte.com renatte.com soft.renatte.com 49.233.160.241` | |

> `client_max_body_size` 在 server 级别设置（不在 location 块内），因为 location 块内的设置对某些路由不生效。

---

## 4. Node.js 应用配置

### 4.1 环境变量

```bash
NODE_ENV=production
PORT=3000
EMAIL_HOST=smtp.163.com
EMAIL_PORT=465
EMAIL_USER=zhouzhk2022@163.com
EMAIL_PASS=DE67SZjQ9hdEhYRi  # SMTP 授权码
```

### 4.2 中间件栈

```
1. helmet (安全头基础)
2. CORS (白名单: www.renatte.com, renatte.com)
3. cookie-parser
4. bodyParser.json
5. 自定义安全头 (CSP/HSTS/XFO 等)
6. 静态文件 (express.static)
7. 路由处理
8. 404 处理
9. 全局错误处理
```

### 4.3 认证体系

| 层级 | 机制 | 存储 |
|------|------|------|
| 会话 | `x-admin-token` header → `sessions` Map | 内存 (24h 过期) |
| CSRF | Double-Submit Cookie 模式 | 内存 Map (4h 过期) |
| 登录 | 密码 (PBKDF2-SHA512) + 邮箱 OTP (6位) | 密码: JSON文件, OTP: 内存 Map (5min 过期) |
| 验证码 | SVG 图形验证码 (4位) | 内存 Map (5min 过期) |

> **注意**：会话、CSRF token、OTP、验证码均为**内存存储**。PM2 重启后全部清空。

### 4.4 关键文件路径

| 文件 | 路径 (服务器) |
|------|--------------|
| 应用入口 | `/home/ubuntu/renatte-website/server/server.js` |
| 管理员配置 | `/home/ubuntu/renatte-website/data/admin-config.json` |
| 分析数据 | `/home/ubuntu/renatte-website/data/analytics/` |
| 审计日志 | `/home/ubuntu/renatte-website/data/audit-log.json` |
| 上传文件 | `/var/www/html/downloads/` |
| PM2 配置 | `/home/ubuntu/renatte-website/ecosystem.config.js` |

### 4.5 文件上传

| 参数 | 值 |
|------|-----|
| 存储目录 | `/var/www/html/downloads/` |
| 最大大小 | 500MB (Multer + Nginx 双重限制) |
| 允许类型 | `.exe`, `.deb`, `.appimage`, `.dmg`, `.msix`, `.zip`, `.msi` |
| 权限 | `ubuntu:www-data`, 775 |

---

## 5. 部署流程

### 5.1 代码部署

```bash
# 1. 上传更新文件
scp -i C:\Users\zhouzhk\.ssh\renatte_server <本地文件> ubuntu@49.233.160.241:/tmp/

# 2. 替换到工作目录
sudo cp /tmp/<文件> /home/ubuntu/renatte-website/<路径>

# 3. 重启 Node.js
pm2 restart server

# 4. 重载 Nginx（仅配置变更时）
sudo nginx -t && sudo systemctl reload nginx
```

### 5.2 Git 信息

> ⚠️ 服务器上**无 Git 仓库**，代码通过 `scp` 手动上传。

| 项目 | 值 |
|------|-----|
| 远程 | `https://gitee.com/zhouzhk/webstie.git` |
| 分支 | `master` |
| 本地开发路径 | `D:\work\webstie`（Windows）/ `/media/zhouzhk/Data/work/renatte-site`（Linux） |
| SSH 密钥 | `~/.ssh/renatte_server`（Ed25519） |

---

## 6. 维护命令速查

### SSH 登录
```bash
ssh -i ~/.ssh/renatte_server ubuntu@49.233.160.241
```

### 服务管理
```bash
pm2 list                           # 所有进程
pm2 restart server                 # 重启官网
pm2 restart goldclaw               # 重启股票分析
pm2 logs server --lines 50         # 官网日志
pm2 logs goldclaw --lines 50       # 股票分析日志

sudo nginx -t                      # 测试 Nginx 配置
sudo systemctl reload nginx        # 重载 Nginx
sudo systemctl status nginx        # Nginx 状态

# 检查配置是否有违规 alias/root
grep -E '^\s+(alias|root)\s' /etc/nginx/sites-enabled/renatte-website && echo '❌' || echo '✅'
```

### 日志位置
```bash
/var/log/nginx/access.log          # Nginx 访问日志
/var/log/nginx/error.log           # Nginx 错误日志
/home/ubuntu/.pm2/logs/            # PM2 应用日志
/home/ubuntu/renatte-website/data/audit-log.json  # 审计日志
/var/log/letsencrypt/letsencrypt.log              # Certbot 日志
```

---

## 7. 变更记录

| 日期 | 版本 | 内容 |
|------|------|------|
| 2026-07-08 | v1.7 | 全面 Nginx 纯反代整改（移除 renattemd/downloads 的 alias）|
| 2026-07-08 | v1.6 | latest.json 移至 `/downloads/`，旧路径软链接兼容 |
| 2026-06-30 | v1.5 | RenatteMD 0.9.2 发布，更新下载文件 |
| 2026-05-25 | v1.4 | 修复上传 body size + OTP 诊断日志 |
| 2026-05-25 | v1.3 | 修复认证 Bug（去 cookie 双通道）+ 文件权限 |
| 2026-05-24 | v1.2 | Nginx 纯反向代理整改（移除 admin alias） |
| 2026-05-23 | v1.1 | 管理后台登录流程 + CSRF 防护 |

---

## 8. 经验教训

1. **client_max_body_size 必须在 server 级别设置**，location 块内可能不生效
2. **双重认证通道 (cookie + sessionStorage) 是定时炸弹**，生命周期不一致导致死循环
3. **PM2 重启清空所有内存 Map**：OTP / session / CSRF token 全部丢失
4. **Nginx 严禁 alias/root**：绕过应用层鉴权的根本原因。`/admin/`、`/renattemd/`、`/downloads/` 均已整改
5. **Nginx backup 禁止放 sites-enabled/**：`include /etc/nginx/sites-enabled/*` 会匹配备份文件，导致 `limit_req_zone` 重复定义
6. **OTP/验证码明文禁止记入日志**，用长度代替
7. **每次 Nginx 改完必须 `nginx -t`**，再 `reload`
8. **服务器是多用途共享的**，改 Nginx 时需注意不影响 goldclaw、iRedMail 等其他站点
