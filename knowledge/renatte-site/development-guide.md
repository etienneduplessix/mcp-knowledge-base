# 开发与运维指南 — renatte-site

## 本地开发

```bash
npm install                 # 安装依赖
npm run dev                 # 启动服务（node server/server.js），默认 :3000
npm run lint                # eslint js/**/*.js
npm run format              # prettier 格式化
node scripts/check-i18n.js  # i18n key 校验（exit 0 为通过）
```

## 国际化开发规范（重要）

新增翻译内容的步骤：
1. HTML 元素加 `data-i18n="section.key"`（点分隔路径）
2. 元素内容写默认中文文本作为 fallback
3. 在 `locales/zh.js` 和 `locales/en.js` 添加对应 key 的翻译
4. 运行 `node scripts/check-i18n.js` 验证无遗漏（exit 0）

注意：
- key 路径格式 `section.subsection.key`，需与翻译对象层级一致
- 含 HTML 标签的翻译（如 footer.copyright 含 `<a>`）用 innerHTML 场景处理
- 数组类型翻译支持索引语法 `weekdays[0]`
- 不允许在 HTML 中直接写非占位文本

## 部署流程（生产）

```bash
# 1. 上传更新文件
scp <本地文件> ubuntu@49.233.160.241:/tmp/

# 2. 替换到工作目录
sudo cp /tmp/<文件> /home/ubuntu/renatte-website/<路径>

# 3. 重启 Node.js
pm2 restart server

# 4. 重载 Nginx（仅配置变更时）
sudo nginx -t && sudo systemctl reload nginx
```

## 运维速查

| 操作 | 命令 |
|------|------|
| SSH 登录 | `ssh ubuntu@49.233.160.241` |
| 服务管理 | `pm2 restart server` / `pm2 logs server` / `pm2 status` |
| Nginx 检查 | `sudo nginx -t && sudo systemctl reload nginx`（检查违规 alias/root） |
| SSL 续期 | Certbot（Let's Encrypt），`scripts/tools/certbot_expand.py` 等脚本 |
| 数据修复 | `scripts/tools/fix_downloads.py` / `fix_renattemd.py` 等 |

## 关键路径（生产）

- 工作目录：`/home/ubuntu/renatte-website/`
- 下载文件目录：`/var/www/html/downloads`
- RenatteMD 目录：`/var/www/html/renattemd`
- 上传文件：`data/uploads/`
- 日志：见知识库 `docs/renatte-site/SERVER-SPEC.md` 第 6 节

## 环境变量（server 端）

- `PORT`（默认 3000）、`dotenv` 加载 `.env`
- 邮件：`nodemailer` 配置（OTP 发送到 `zhouzhk2022@163.com`）

## 变更记录参考

- i18n 重构 v2.0（2026-07）：翻译数据拆分 + `data-i18n` 统一机制，详见 `04-module-i18n.md`
- analytics-db v2.1.0（2026-07-11）：SQLite 迁移 + 数据详情查看，详见 `04-module-analytics-db.md`

## 注意事项 / 经验教训

- Nginx 必须纯代理，禁止在 Nginx 层直接返回静态文件（架构铁律）
- 相对路径/下载目录在 server.js 中有 `/var/www/html` 判断分支，本地与生产路径不同
- SQLite 使用 WAL + `synchronous=NORMAL`；不自动 VACUUM（写入自动复用空闲空间）
- 会话/CSRF token 存内存，重启丢失属预期行为
