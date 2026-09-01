# 南京瑞纳特智能技术有限公司官网

[![License](https://img.shields.io/badge/license-Academic%20Free%20License%20v3.0-blue)](LICENSE)
[![Website](https://img.shields.io/badge/website-live-green)](https://www.renatte.com)
[![HTML5](https://img.shields.io/badge/HTML5-E34F26?logo=html5&logoColor=white)](https://developer.mozilla.org/en-US/docs/Web/HTML)
[![Tailwind CSS](https://img.shields.io/badge/Tailwind-38B2AC?logo=tailwind-css&logoColor=white)](https://tailwindcss.com)

## 📋 项目简介

南京瑞纳特智能技术有限公司官方网站，专注于智能园区软件平台的开发与运营展示。网站采用现代化设计风格，支持中英文双语切换，为企业客户提供智慧园区数字化解决方案的全面介绍。

## ✨ 核心特性

### 🎨 设计特点
- **现代化UI设计** - 采用玫瑰粉(#C0175B)作为品牌主色调，搭配深蓝(#0F172A)形成优雅对比
- **毛玻璃效果** - 导航栏使用backdrop-filter实现磨砂玻璃效果
- **流畅动画** - 滚动渐入、卡片悬浮、浮动动画等交互效果
- **响应式布局** - 完美适配桌面端、平板和移动端设备
- **视觉一致性** - 统一的色彩系统和间距规范

### 🛠️ 技术实现
- **轻量级架构** - 无需构建工具，直接在浏览器中运行
- **模块化CSS** - 独立的样式文件，便于维护和扩展
- **纯JavaScript** - 无框架依赖，性能优异
- **SEO优化** - 完整的meta标签和语义化HTML结构
- **多语言支持** - 内置中英文双语切换功能

### 🌐 功能模块
1. **导航栏** - 响应式导航，支持滚动效果和移动端菜单
2. **Hero区域** - 品牌展示、数据统计、交互式仪表盘
3. **产品服务** - 9个核心产品卡片展示
4. **核心优势** - 技术可视化与4大核心优势说明
5. **典型案例** - 5个实际案例展示
6. **关于我们** - 公司简介、发展历程时间线
7. **联系表单** - 完整的咨询表单与联系方式
8. **页脚** - 快速链接与版权信息

## 📁 项目结构

```
webstie/
├── index.html              # 主页面文件
├── css/
│   ├── style.css           # 主样式文件
│   └── i18n.css          # 国际化样式
├── js/
│   ├── script.js           # 核心脚本
│   └── i18n.js            # 国际化支持
├── renatte_icon.png        # Logo (PNG格式)
├── renatte_icon.webp       # Logo (WebP优化格式)
├── optimize_images.bat      # 图片优化脚本
├── README.md              # 项目说明文档(中文)
├── README.en.md           # 项目说明文档(英文)
└── LICENSE                # 开源协议
```

## 🚀 快速开始

### 本地运行

1. **克隆项目**
   ```bash
   git clone https://github.com/your-username/webstie.git
   cd webstie
   ```

2. **直接打开**
   - 双击 `index.html` 文件
   - 或使用任何HTTP服务器（如VS Code Live Server）
   ```bash
   # 使用Python
   python -m http.server 8000
   
   # 使用Node.js
   npx serve
   
   # 使用VS Code扩展
   # 安装 "Live Server" 扩展，右键选择 "Open with Live Server"
   ```

3. **访问网站**
   - 浏览器访问 `http://localhost:8000`

### 部署到生产环境

#### 方法1：静态托管平台
- **GitHub Pages** - 免费托管，自动CI/CD
- **Vercel** - 全球CDN，零配置部署
- **Netlify** - 拖拽部署，自动HTTPS

#### 方法2：传统服务器
```bash
# 上传文件到服务器
scp -r * user@your-server.com:/var/www/html

# 或使用FTP工具上传
```

#### 方法3：云服务集成
项目已适配以下云服务部署：
- **腾讯云EdgeOne Pages** - 前端静态托管
- **腾讯云CloudBase** - 全栈云开发
- **阿里云OSS** - 对象存储 + CDN

## 🎯 功能详解

### 多语言支持

网站内置完整的中英文双语支持：
- 自动检测浏览器语言
- 手动切换语言（右上角按钮）
- 语言偏好本地存储
- 支持SEO友好的URL结构

使用方法：
```javascript
// 初始化
i18n.init();

// 切换语言
i18n.setLanguage('en');  // 切换到英文
i18n.setLanguage('zh');  // 切换到中文
```

### 图片优化

项目使用WebP格式优化图片加载：

1. **准备环境**
   - Windows: 下载 [cwebp](https://developers.google.com/speed/webp/docs/cwebp)
   - macOS: `brew install webp`
   - Linux: `sudo apt-get install webp`

2. **运行优化脚本**
   ```bash
   # Windows
   optimize_images.bat
   
   # Linux/macOS
   cwebp -q 85 renatte_icon.png -o renatte_icon.webp
   ```

3. **使用picture元素**
   ```html
   <picture>
     <source srcset="image.webp" type="image/webp">
     <img src="image.png" alt="描述" />
   </picture>
   ```

### 表单集成

当前表单为前端模拟，如需接入后端：

1. **修改`js/script.js`中的`submitForm`函数**
   ```javascript
   function submitForm(e) {
     e.preventDefault();
     const formData = new FormData(e.target);
     
     // 发送到后端API
     fetch('https://api.renatte.com/contact', {
       method: 'POST',
       body: formData
     })
     .then(response => response.json())
     .then(data => {
       // 处理成功响应
       showSuccessMessage();
     })
     .catch(error => {
       // 处理错误
       showErrorMessage();
     });
   }
   ```

2. **后端API建议**
   - 邮件服务：SendGrid / 阿里云邮件推送
   - CRM集成：销售易 / 纷享销客
   - 表单服务：Formspree / Netlify Forms

## 🎨 自定义配置

### 修改品牌色

编辑`css/style.css`中的CSS变量：
```css
:root {
  --rose-brand: #C0175B;    /* 主品牌色 */
  --rose-light: #E8417D;    /* 浅品牌色 */
  --rose-dark: #8C0F42;     /* 深品牌色 */
  --navy: #0F172A;          /* 深色系 */
  --muted: #64748B;         /* 灰色系 */
}
```

### 添加新语言

在`js/i18n.js`中添加新的语言翻译：

```javascript
translations: {
  zh: { /* 中文翻译 */ },
  en: { /* 英文翻译 */ },
  ja: { /* 添加日文 */ }  // 新语言
}
```

## 🔧 开发工具推荐

| 工具 | 用途 | 推荐版本 |
|------|------|---------|
| VS Code | 代码编辑器 | 最新版 |
| Live Server | 本地开发服务器 | 5.7+ |
| Chrome DevTools | 调试 | 内置 |
| Prettier | 代码格式化 | 3.0+ |
| ESLint | 代码检查 | 8.0+ |

## 📊 性能优化建议

### 已实施优化
- ✅ CSS提取为独立文件
- ✅ JavaScript模块化
- ✅ WebP图片格式
- ✅ CDN加载Tailwind CSS
- ✅ 语义化HTML标签
- ✅ 懒加载动画

### 进一步优化
- [ ] 启用Gzip压缩
- [ ] 配置CDN加速
- [ ] 实施图片懒加载
- [ ] 添加Service Worker缓存
- [ ] 预加载关键资源
- [ ] 实施代码分割

## 🌐 浏览器兼容性

| 浏览器 | 版本要求 |
|---------|---------|
| Chrome | 90+ |
| Firefox | 88+ |
| Safari | 14+ |
| Edge | 90+ |
| Opera | 76+ |

不支持IE浏览器。

## 🤝 贡献指南

欢迎贡献代码！请遵循以下步骤：

1. Fork本仓库
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启Pull Request

### 代码规范
- 使用2空格缩进
- 遵循现有命名约定
- 添加必要的注释
- 确保所有浏览器兼容性

## 📄 开源协议

本项目采用 [Academic Free License v3.0](LICENSE) 开源协议。

## 📞 联系方式

- **公司地址**：江苏省南京市高淳区桠溪街道永尚村桠云路69号
- **官方网站**：https://www.renatte.com
- **商务邮箱**：info@renatte.com

## 🙏 致谢

感谢以下开源项目：
- [Tailwind CSS](https://tailwindcss.com) - CSS框架
- [Google Fonts](https://fonts.google.com) - 字体服务
- [Lucide](https://lucide.dev) - 图标库

---

**南京瑞纳特智能技术有限公司** © 2026. All rights reserved.
