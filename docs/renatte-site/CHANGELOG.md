# 更新日志 / Changelog

所有值得注意的项目更改都将记录在此文件中。

本文档格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/)，
并且本项目遵循[语义化版本](https://semver.org/lang/zh-CN/)。

## [未发布] - 未来计划

### 计划
- 添加暗黑模式支持
- 实施服务端渲染(SSR)提升SEO
- 添加网站分析(Google Analytics/百度统计)
- 集成真实的表单提交API
- 添加博客/新闻动态模块
- 实施PWA支持
- 添加单元测试和集成测试
- 多语言SEO优化
- 图片懒加载优化
- Service Worker缓存策略

## [2.0.0] - 2026-03-15

### 新增
- **代码结构优化**
  - 提取CSS到独立文件(`css/style.css`)
  - 提取JavaScript到独立文件(`js/script.js`)
  - 模块化代码结构，提升可维护性
- **SEO优化**
  - 添加完整的meta标签(keywords, description, author, robots)
  - 添加Open Graph元数据
  - 添加Twitter Card支持
  - 添加canonical链接
  - 添加主题色配置
- **多语言支持**
  - 实现中英文双语切换功能
  - 创建国际化模块(`js/i18n.js`)
  - 支持浏览器语言自动检测
  - 语言偏好本地存储
  - 添加语言切换器UI
- **图片优化**
  - 添加WebP格式支持
  - 使用`<picture>`元素实现渐进式加载
  - 提供图片优化脚本(`optimize_images.bat`)
- **文档完善**
  - 重写`README.md`，包含详细的项目说明
  - 创建`README.en.md`英文版本文档
  - 添加快速开始指南
  - 添加功能详解文档
  - 添加自定义配置说明
  - 创建更新日志文档
- **性能优化**
  - 分离CSS和JavaScript文件
  - 减少HTML文件大小
  - 优化图片加载策略

### 技术变更
- 将Tailwind配置保留在HTML中(用于运行时)
- 所有样式迁移到独立CSS文件
- 所有JavaScript逻辑迁移到独立JS文件
- 添加i18n支持模块

### 文档
- 新增`README.md` - 完整的中文项目文档
- 新增`README.en.md` - 完整的英文项目文档
- 新增`CHANGELOG.md` - 版本更新日志
- 新增`css/style.css` - 样式文件说明
- 新增`css/i18n.css` - 国际化样式
- 新增`js/script.js` - 脚本功能说明
- 新增`js/i18n.js` - 国际化功能说明
- 新增`optimize_images.bat` - 图片优化说明

## [1.0.0] - 初始版本

### 新增
- 首次发布南京瑞纳特智能技术有限公司官方网站
- 实现完整的公司展示页面
- 9个产品服务模块展示
- 核心优势展示(4大优势)
- 5个典型案例展示
- 公司介绍与发展历程时间线
- 联系表单与联系方式
- 响应式导航栏(支持移动端)
- Hero区域交互式仪表盘可视化
- 页脚信息与快速链接
- 完整的SEO基础设置
- 现代化UI设计与动画效果

### 技术实现
- 使用HTML5语义化标签
- Tailwind CSS快速样式开发
- 纯JavaScript实现交互
- 无构建工具依赖
- 单页应用(SPA)架构

---

**注**: 版本号格式为 `主版本.次版本.修订版本`
- **主版本**: 重大架构变更或不兼容更新
- **次版本**: 新增功能，向后兼容
- **修订版本**: Bug修复或小改进
