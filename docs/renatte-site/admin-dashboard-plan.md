# 官网管理后台 - 实施计划

创建时间: 2026-05-23 16:00

## 目标

为 www.renatte.com 创建管理后台，提供：
1. 官网访问量查看（PV/UV）
2. RenatteMD 各端/版本下载量查看
3. 新版本文件上传
4. 管理员密码修改

## 架构

- 基于现有 Express.js (port 3000) 扩展
- 数据存储：JSON 文件（轻量级，无需额外数据库）
- 前端：纯 HTML/CSS/JS 单页面管理后台
- 认证：Session + Cookie（简单 token 验证）
- Nginx 配置：`/admin` 路径代理到 Express

## 步骤

### Phase 1: 数据追踪扩展
- [ ] 创建 analytics 数据模型（访问量、下载量）
- [ ] 添加下载追踪 API（/api/analytics/download）
- [ ] 添加页面访问追踪 API（/api/analytics/pageview）
- [ ] 添加 Nginx 下载日志记录

### Phase 2: 管理后端 API
- [ ] 认证中间件（session/token）
- [ ] 登录 API（/api/admin/login）
- [ ] 获取统计 API（/api/admin/stats）
- [ ] 文件上传 API（/api/admin/upload）
- [ ] 密码修改 API（/api/admin/password）

### Phase 3: 管理前端页面
- [ ] 登录页面（admin/login）
- [ ] 仪表盘（访问量趋势图）
- [ ] 下载统计（分平台、分版本）
- [ ] 文件上传界面
- [ ] 密码修改界面

### Phase 4: Nginx 配置
- [ ] 添加 /admin location 代理

### Phase 5: 部署测试
- [ ] 上传所有文件到服务器
- [ ] 安装必要依赖
- [ ] 配置 Nginx
- [ ] 重启服务
- [ ] 功能测试

## 技术细节

### 数据存储结构
```
data/
├── admin-config.json    # 管理员配置（密码 hash）
├── analytics/
│   ├── pageviews.json   # 页面访问记录
│   └── downloads.json   # 下载记录
└── uploads/             # 上传临时目录
```

### 安全考虑
- 密码使用 bcrypt 加密存储
- Session token 过期机制
- 文件上传大小限制（200MB）
- 文件类型白名单校验（.exe, .deb, .AppImage, .dmg）
- 上传文件权限控制

## 当前进度

正在执行: Phase 1
