# 163邮箱SMTP配置指南

## 前置准备

1. 登录网页版163邮箱
2. 进入 **设置** → **POP3/SMTP/IMAP**
3. 开启 `SMTP服务` 并勾选 `SSL加密`
4. 完成手机验证后获取 **授权码** (重要)

## 项目配置

### .env 文件配置

```env
# 服务器配置
NODE_ENV=production
PORT=3000

# 163邮件服务配置
EMAIL_HOST=smtp.163.com
EMAIL_PORT=465
EMAIL_USER=your_email@163.com
EMAIL_PASS=your_authorization_code  # 注意：这里是授权码，不是登录密码！
```

### server.js 中的配置

服务器已支持163邮箱配置，只需更新 .env 文件即可。

## 部署步骤

### 本地测试

1. 复制 `.env.example` 为 `.env`
2. 填入您的163邮箱信息（使用授权码）
3. 重启服务测试邮件发送

### 服务器部署

```bash
# 连接到服务器
ssh ubuntu@49.233.160.241

# 进入项目目录
cd ~/renatte-website

# 编辑 .env 文件
nano .env

# 修改以下内容：
# EMAIL_HOST=smtp.163.com
# EMAIL_PORT=465
# EMAIL_USER=your_email@163.com
# EMAIL_PASS=your_authorization_code

# 保存并退出后，重启服务
pm2 restart server
```

## 注意事项

1. **使用授权码**：不要使用登录密码，必须使用SMTP授权码
2. **端口选择**：推荐使用 465 (SSL)，避免使用 25
3. **发送限制**：163免费邮箱每日发送上限500封
4. **安全建议**：定期更新授权码，保护账户安全

## 验证配置

部署后可通过管理后台的 OTP 发送功能验证邮件服务是否正常工作。
