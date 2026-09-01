# 瑞纳特官网部署手册

> **项目**: renatte-site（南京瑞纳特智能技术有限公司官网）
> **生产服务器**: 腾讯云 `49.233.160.241`
> **主机名**: `mail`（多用途服务器，同时运行邮件、数据库等服务）
> **系统**: Ubuntu 24.04.4 LTS
> **最后更新**: 2026-07-08（基于服务器实时数据）

---

## 目录

1. [服务器规格](#1-服务器规格)
2. [服务架构](#2-服务架构)
3. [前置准备](#3-前置准备)
4. [部署方式](#4-部署方式)
5. [SSL 证书管理](#5-ssl-证书管理)
6. [常用维护命令](#6-常用维护命令)
7. [诊断与修复工具](#7-诊断与修复工具)
8. [安全配置](#8-安全配置)
9. [经验教训](#9-经验教训)
10. [故障排查](#10-故障排查)

---

## 1. 服务器规格

### 1.1 硬件信息

| 项目 | 实际值 |
|------|--------|
| 服务商 | 腾讯云轻量应用服务器 |
| IP 地址 | `49.233.160.241` |
| 主机名 | `mail` |
| 操作系统 | Ubuntu 24.04.4 LTS (Kernel 6.8.0-71-generic) |
| CPU | Intel Xeon Gold 6148 @ 2.40GHz (4 vCPU) |
| 内存 | 3.6 GiB（可用 ~1.4 GiB） |
| 磁盘 | 69 GiB（已用 37 GiB / 56%） |
| Swap | 9.9 GiB（已用 1.8 GiB） |
| 运行时间 | 118 天（自 2026-03-11 起） |

### 1.2 运行时版本

| 组件 | 版本 |
|------|------|
| Node.js | v20.20.2 |
| npm | 10.8.2 |
| Nginx | 1.24.0 (Ubuntu) |
| PM2 | 7.0.1 |
| Docker | 29.5.3（已安装，未使用） |
| MariaDB | 10.11.14 |
| Redis | 7.x（`127.0.0.1:6379`） |

### 1.3 域名

| 域名 | 用途 |
|------|------|
| `www.renatte.com` | 主站 |
| `renatte.com` | 裸域名（301 重定向到 www） |
| `soft.renatte.com` | 软件下载子域 |
| `mail.renatte.com` | 邮件服务 |
| `goldclaw.renatte.com` | 股票分析工具 |

### 1.4 同机部署的其它服务

本服务器除瑞纳特官网外，还运行以下服务：

| 服务 | 端口 | 说明 |
|------|------|------|
| iRedMail | `:80/:443` 共享 | 邮件系统（dovecot, postfix, roundcube） |
| GoldClaw | `127.0.0.1:8000` | 股票数据分析 WebUI，Nginx 代理至 `goldclaw.renatte.com` |
| MariaDB | `127.0.0.1:3306` | 数据库 |
| Redis | `127.0.0.1:6379` | 缓存 |
| Fail2ban | 后台 | 6 个 jails: dovecot, nginx-http-auth, postfix, pregreet, roundcube, sshd |

---

## 2. 服务架构

### 2.1 核心原则

> **Nginx 在本项目中唯一角色：纯反向代理。严禁使用 `alias` 或 `root` 直接返回静态内容。**
>
> - ❌ 禁止 `alias`、`root`、`try_files` 从 Nginx 直接返回文件
> - ❌ 禁止在 Nginx 中直接返回静态 HTML/CSS/JS
> - ✅ 所有请求必须统一 `proxy_pass http://127.0.0.1:3000`
> - ✅ Node.js 负责：会话鉴权、审计日志、CSP 设置、缓存策略、静态文件服务

> **血泪教训**：旧配置中 `/renattemd/` 和 `/downloads/` 使用了 `alias`，导致 Nginx 绕过 Node.js 直接返回文件。
> 2026-07-08 已全部整改为 `proxy_pass`。

### 2.2 架构概览

```
                           ┌─────────────────────────────┐
                           │         浏览器 (Client)        │
                           └─────────────┬───────────────┘
                                         │ HTTPS (:443)
                                         ▼
                           ┌─────────────────────────────┐
                           │   Nginx 1.24.0 (:80 / :443)  │
                           │   · SSL 终止（Let's Encrypt）  │
                           │   · 纯反向代理到 :3000        │
                           │   · 无 alias/root 指令       │
                           │   · 速率限制（登录/OTP/验证码） │
                           │   · 安全响应头                │
                           │   · HTTP → HTTPS 重定向       │
                           ├─────────────────────────────┤
                           │   Nginx 也代理：              │
                           │   · goldclaw.renatte.com     │
                           │     → 127.0.0.1:8000          │
                           │   · mail.renatte.com         │
                           │     → iRedMail WebUI          │
                           └─────────────┬───────────────┘
                                         │ proxy_pass（每条路由）
                                         ▼
                           ┌─────────────────────────────┐
                           │  Node.js Express (PM2 管理)   │
                           │  · 监听 127.0.0.1:3000       │
                           │  · 静态文件（HTML/CSS/JS/图片） │
                           │  · 管理后台（/admin）          │
                           │  · RenatteMD（/renattemd/）   │
                           │  · 下载文件（/downloads/）    │
                           │  · API（登录/上传/分析）        │
                           │  · CSRF · 会话管理 · CSP       │
                           └─────────────────────────────┘
```

### 2.3 端口清单

| 服务 | 绑定 | 端口 | 说明 |
|------|------|------|------|
| Nginx HTTP | `0.0.0.0` | 80 | 301 重定向到 HTTPS |
| Nginx HTTPS | `0.0.0.0` | 443 | SSL 终止 + 反向代理 |
| Node.js | `127.0.0.1` | 3000 | Express 应用（PM2 管理） |
| GoldClaw | `0.0.0.0` | 8000 | Python 股票分析 WebUI |
| MariaDB | `127.0.0.1` | 3306 | 数据库 |
| Redis | `127.0.0.1` | 6379 | 缓存 |
| Fail2ban | 后台 | — | SSH/Mail/Web 防护 |

### 2.4 PM2 进程

| 进程名 | 模式 | 内存 | 重启次数 | 运行时间 | 路径 |
|--------|------|------|----------|----------|------|
| `server` | cluster | 41 MB | **73 次** | 2 天 | `/home/ubuntu/renatte-website/server/server.js` |
| `goldclaw` | fork | 692 MB | 3 次 | 28 天 | `/home/ubuntu/daily_stock_analysis/main.py` |

> server 重启 73 次说明开发阶段频繁部署或存在稳定性问题，需关注。

---

## 3. 前置准备

### 3.1 SSH 连接

```bash
# 密钥文件
~/.ssh/renatte_server

# 登录
ssh -i ~/.ssh/renatte_server ubuntu@49.233.160.241
```

### 3.2 工作目录

| 路径 | 说明 |
|------|------|
| `/home/ubuntu/renatte-website/` | 应用主目录 |
| `/home/ubuntu/renatte-website/server/server.js` | Express 入口 |
| `/home/ubuntu/renatte-website/data/` | 数据文件 |
| `/home/ubuntu/renatte-website/data/admin-config.json` | 管理员配置 |
| `/home/ubuntu/renatte-website/data/analytics/` | 访问分析（pageviews.json, downloads.json） |
| `/home/ubuntu/renatte-website/data/audit-log.json` | 审计日志 |
| `/home/ubuntu/renatte-website/data/uploads/` | 上传文件临时目录 |
| `/home/ubuntu/renatte-website/admin/` | 管理后台静态页面 |
| `/home/ubuntu/renatte-website/downloads/` | 下载文件目录 |
| `/var/www/html/downloads/` | 下载文件 + `latest.json`（自动更新主路径） |
| `/var/www/html/renattemd/` | RenatteMD 分发页面 + `latest.json`（旧路径，向后兼容） |
| `/etc/nginx/sites-enabled/renatte-website` | Nginx 配置（**普通文件，非软链接**） |
| `/home/ubuntu/nginx-backups/` | Nginx 配置备份（**禁止放 sites-enabled/**） |
| `/home/ubuntu/.pm2/logs/` | PM2 日志 |

### 3.3 PM2 环境变量

配置文件 `/home/ubuntu/renatte-website/ecosystem.config.js`：

```javascript
module.exports = {
  apps: [{
    name: 'server',
    script: 'server/server.js',
    cwd: '/home/ubuntu/renatte-website',
    env: {
      NODE_ENV: 'production',
      PORT: 3000,
      EMAIL_HOST: 'smtp.163.com',
      EMAIL_PORT: 465,
      EMAIL_USER: 'zhouzhk2022@163.com',
      EMAIL_PASS: '<SMTP授权码>'
    },
    instances: 1,
    autorestart: true,
    watch: false,
    max_memory_restart: '500M',
  }]
};
```

### 3.4 服务器端 package.json

```json
{
  "name": "renatte-website",
  "version": "1.0.0",
  "dependencies": {
    "express": "^4.18.2",
    "body-parser": "^1.20.2",
    "cookie-parser": "^1.4.7",
    "cors": "^2.8.5",
    "dotenv": "^16.3.0",
    "multer": "^2.1.1",
    "nodemailer": "^6.9.0"
  },
  "devDependencies": {
    "nodemon": "^2.0.22",
    "tailwindcss": "^3.4.0"
  }
}
```

---

## 4. 部署方式

### 4.1 SCP + PM2 手动部署（标准方式）

```bash
# 步骤 1: 上传文件到服务器
scp -i ~/.ssh/renatte_server \
  server/server.js \
  ubuntu@49.233.160.241:/tmp/

# 如果有静态文件变更
scp -i ~/.ssh/renatte_server \
  index.html css/style.css js/i18n.js \
  ubuntu@49.233.160.241:/tmp/

# 步骤 2: SSH 登录并部署
ssh -i ~/.ssh/renatte_server ubuntu@49.233.160.241

# 步骤 3: 备份原文件
cp /home/ubuntu/renatte-website/server/server.js \
   /home/ubuntu/renatte-website/server/server.js.bak.$(date +%Y%m%d_%H%M%S)

# 步骤 4: 替换文件
sudo cp /tmp/server.js /home/ubuntu/renatte-website/server/server.js
sudo cp /tmp/index.html /home/ubuntu/renatte-website/
sudo cp /tmp/style.css /home/ubuntu/renatte-website/css/
sudo cp /tmp/i18n.js /home/ubuntu/renatte-website/js/

# 步骤 5: 安装新依赖（如有变更）
cd /home/ubuntu/renatte-website && npm install

# 步骤 6: 重启 PM2
pm2 restart server

# 步骤 7: 验证
pm2 status
curl -s http://127.0.0.1:3000/api/health

# 退出 SSH
exit
```

### 4.2 快速更新（仅 server.js）

```bash
scp -i ~/.ssh/renatte_server server/server.js ubuntu@49.233.160.241:/tmp/
ssh -i ~/.ssh/renatte_server ubuntu@49.233.160.241 \
  "sudo cp /tmp/server.js /home/ubuntu/renatte-website/server/server.js && \
   pm2 restart server"
```

### 4.3 Docker 部署（备选，当前未使用）

项目支持 Docker，但生产**当前未运行 Docker 容器**。

```bash
# 构建并启动
./scripts/tools/deploy.sh production
docker compose up -d --build
```

### 4.4 SSH 脚本自动化

项目 `scripts/tools/` 目录下的 Python 脚本（需 `pip install paramiko`）：

| 脚本 | 功能 |
|------|------|
| `deploy-admin.py` | 一键更新管理后台（server.js + Nginx + PM2 重启） |
| `upload_latest.py` | 上传 `latest.json` 到 `/downloads/`（兼容旧 `/renattemd/`） |
| `fix_downloads.py` | 修复下载路径配置 |
| `fix_renattemd.py` | 创建 RenatteMD 下载页 + 修复路由 |
| `fix_renattemd_route.py` | 修复 `/renattemd` 重定向 |

---

## 5. SSL 证书管理

### 5.1 当前证书

| 证书名 | 域名 | 到期 | 剩余 |
|--------|------|------|------|
| `www.renatte.com-0001` | www.renatte.com, mail.renatte.com, renatte.com, soft.renatte.com | 2026-09-04 | 58 天 |
| `goldclaw.renatte.com` | goldclaw.renatte.com | 2026-08-28 | 51 天 |
| `mail.renatte.com` | mail.renatte.com | 2026-09-03 | 57 天 |

### 5.2 续期

```bash
# 手动续期全部证书
sudo certbot renew

# 测试续期
sudo certbot renew --dry-run
```

### 5.3 检查

```bash
# 列出所有证书
sudo certbot certificates

# 查看单个证书详情
echo | openssl s_client -connect www.renatte.com:443 \
  -servername www.renatte.com 2>&1 | \
  openssl x509 -noout -dates -subject -issuer
```

---

## 6. 常用维护命令

### 6.1 SSH 登录

```bash
ssh -i ~/.ssh/renatte_server ubuntu@49.233.160.241
```

### 6.2 PM2

```bash
pm2 list                        # 查看所有进程
pm2 restart server              # 重启官网
pm2 restart goldclaw            # 重启股票分析
pm2 logs server --lines 50      # 官网日志
pm2 logs goldclaw --lines 50    # 股票分析日志
pm2 status                      # 状态
pm2 flush                       # 清空日志
```

### 6.3 Nginx

```bash
sudo nginx -t                   # 测试配置
sudo systemctl reload nginx     # 重载（不停机）
sudo systemctl status nginx     # 状态
tail -f /var/log/nginx/access.log
tail -f /var/log/nginx/error.log

# 检查配置中是否有违规的 alias/root
grep -E '^\s+(alias|root)\s' /etc/nginx/sites-enabled/renatte-website && \
  echo '❌ 发现违规指令' || echo '✅ 无 alias/root'
```

> ⚠️ **重要**：Nginx 配置统一使用 `include /etc/nginx/sites-enabled/*;`
> 备份文件**不得放在** `sites-enabled/` 目录下，否则会被一并加载导致配置冲突。
> 备份应放到 `/home/ubuntu/nginx-backups/`。

### 6.4 应用管理

```bash
# 网站根目录
cd /home/ubuntu/renatte-website

# 安装依赖
npm install

# 查看数据分析
cat /home/ubuntu/renatte-website/data/analytics/pageviews.json | python3 -m json.tool
```

### 6.5 日志位置

| 日志 | 路径 |
|------|------|
| Nginx 访问 | `/var/log/nginx/access.log` |
| Nginx 错误 | `/var/log/nginx/error.log` |
| PM2 输出 | `/home/ubuntu/.pm2/logs/server-out-0.log` |
| PM2 错误 | `/home/ubuntu/.pm2/logs/server-error-0.log` |
| 审计日志 | `/home/ubuntu/renatte-website/data/audit-log.json` |
| Certbot | `/var/log/letsencrypt/letsencrypt.log` |

---

## 7. 诊断与修复工具

位于 `scripts/tools/` 目录（需要 `pip install paramiko`）：

| 脚本 | 功能 |
|------|------|
| `check_ssl.py` | 检查证书到期时间、证书链完整性 |
| `check_soft.py` | 检查 `soft.renatte.com` 子域名路由 |
| `simulate_browser.py` | 模拟浏览器多 UA 测试部署 |
| `certbot_expand.py` | 扩展证书到新域名 |
| `deploy-admin.py` | 一键部署管理后台 |
| `upload_latest.py` | 上传 RenatteMD 版本信息 |
| `fix_downloads.py` | 修复下载路径 Nginx 配置 |
| `fix_renattemd.py` | 创建 RenatteMD 页面 + 修复路由 |
| `fix_renattemd_route.py` | 修复 `/renattemd` 重定向 |

---

## 8. 安全配置

### 8.1 当前安全状态

| 项目 | 状态 |
|------|------|
| UFW 防火墙 | ❌ 未启用 |
| Fail2ban | ✅ 6 个 jails（ssh, nginx, dovecot, postfix, etc.）|
| Let's Encrypt SSL | ✅ TLSv1.2/v1.3 |
| 速率限制 | ✅ 登录 5r/m, OTP 3r/m, 验证码 30r/m |
| 安全响应头 | ✅ HSTS, CSP, XFO, XSS 等 |

### 8.2 UFW（建议启用）

```bash
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
sudo ufw status verbose
```

### 8.3 Fail2ban

```bash
sudo fail2ban-client status                       # 所有 jails
sudo fail2ban-client status sshd                  # 特定 jail
sudo fail2ban-client set sshd unbanip <IP>        # 解封 IP
```

### 8.4 Nginx Location 路由与速率限制

所有 location 均为纯反向代理（`proxy_pass http://127.0.0.1:3000`），无 `alias`/`root`。

| 优先级 | Location | 说明 | 速率限制 |
|--------|----------|------|----------|
| 1 | `= /` | 首页（强制不缓存） | 无 |
| 2 | `/api/admin/login` | 登录接口 | `login` 5r/m, burst 3 |
| 3 | `/api/admin/send-otp` | OTP 发送 | `otp` 3r/m, burst 2 |
| 4 | `/api/captcha` | 验证码 | `captcha` 30r/m, burst 10 |
| 5 | `/admin` | 管理后台 | 无 |
| 6 | `/renattemd/` | RenatteMD 静态文件 | 无（Node.js 处理缓存头） |
| 7 | `/downloads/` | 下载文件 | 无（Node.js 处理缓存头） |
| 8 | `/` | 所有其他请求（兜底） | 无 |

---

## 9. 经验教训

> 项目历史踩坑记录，务必遵守。

1. **`client_max_body_size` 必须在 server 级别设置**，location 块内可能不生效。
2. **PM2 重启清空所有内存数据**：OTP、Session、CSRF token 全部丢失，重启后需重新登录。
3. **Nginx 严禁 `alias`/`root`**：绕过应用层鉴权的根本原因。2026-05-24 修复 `/admin/`，2026-07-08 修复 `/renattemd/` 和 `/downloads/`。
4. **Nginx `sites-enabled/` 目录下不得存放备份文件**：`include /etc/nginx/sites-enabled/*;` 会匹配备份文件，导致 `limit_req_zone` 重复定义报错。备份请放到 `/home/ubuntu/nginx-backups/`。
5. **OTP/验证码明文禁止记入日志**，用长度代替内容。
6. **每次 Nginx 改完必须 `nginx -t`，再 `reload`**。
7. **Nginx 配置必须有备份**，改前 `cp` 带时间戳。
8. **服务器是共享的**，改 Nginx 时需注意不影响 goldclaw 和 iRedMail 等其他站点。
9. **上传文件检查磁盘空间**：`df -h`，当前已用 56%。

---

## 10. 故障排查

### 10.1 首页 502

```bash
pm2 status                     # PM2 是否运行？
curl http://127.0.0.1:3000/   # Node.js 是否响应？
sudo systemctl status nginx    # Nginx 状态
```

### 10.2 管理后台无法登录

```bash
pm2 logs server --lines 30     # 查看 PM2 日志
cat data/audit-log.json | tail -20  # 审计日志
# PM2 重启后所有 session 已清空，需重新登录
```

### 10.3 SSL 证书问题

```bash
sudo certbot certificates
python scripts/tools/check_ssl.py
```

### 10.4 文件上传失败

```bash
df -h                          # 磁盘空间
ls -la /home/ubuntu/renatte-website/data/uploads/
cat /home/ubuntu/renatte-website/data/audit-log.json | grep upload
```

### 10.5 邮件发送失败

```bash
pm2 env server | grep EMAIL    # 环境变量
telnet smtp.163.com 465        # SMTP 可达性
```

---

## 附录

### A. 关键文件清单

| 文件 | 服务端路径 | 项目本地路径 |
|------|-----------|-------------|
| PM2 配置 | `/home/ubuntu/renatte-website/ecosystem.config.js` | — |
| Nginx 配置（生效） | `/etc/nginx/sites-enabled/renatte-website` | — |
| Nginx 模板（同步源） | `/home/ubuntu/renatte-website/renatte-website-nginx.conf` | `renatte-website-nginx.conf` |
| Nginx 备份 | `/home/ubuntu/nginx-backups/` | — |
| Dockerfile | `/home/ubuntu/renatte-website/Dockerfile` | `Dockerfile` |
| Docker Compose | `/home/ubuntu/renatte-website/docker-compose.yml` | `docker-compose.yml` |
| 环境变量 | `/home/ubuntu/renatte-website/.env` | — |

> 修改 Nginx 配置后，需同时同步项目本地 `renatte-website-nginx.conf` 以保持版本一致。

### B. 引用文档

| 文档 | 说明 |
|------|------|
| `SERVER-SPEC.md`（已归档至知识库 `docs/renatte-site/`） | 服务器配置详细规格 |
| `specs/02-tech.md` | 技术架构规范 |
| `CHANGELOG.md` | 发布历史 |
