# Nanjing Renatte Intelligent Technology Co., Ltd. Official Website

[![License](https://img.shields.io/badge/license-Academic%20Free%20License%20v3.0-blue)](LICENSE)
[![Website](https://img.shields.io/badge/website-live-green)](https://www.renatte.com)
[![HTML5](https://img.shields.io/badge/HTML5-E34F26?logo=html5&logoColor=white)](https://developer.mozilla.org/en-US/docs/Web/HTML)
[![Tailwind CSS](https://img.shields.io/badge/Tailwind-38B2AC?logo=tailwind-css&logoColor=white)](https://tailwindcss.com)

## 📋 Project Overview

Official website of Nanjing Renatte Intelligent Technology Co., Ltd., showcasing smart park software platform development and operations. The website features modern design with bilingual Chinese-English support, providing comprehensive introduction of smart park digital solutions for enterprise clients.

## ✨ Core Features

### 🎨 Design Highlights
- **Modern UI Design** - Rose pink (#C0175B) as brand primary color, paired with deep blue (#0F172A) for elegant contrast
- **Glassmorphism Effect** - Navigation bar uses backdrop-filter for frosted glass effect
- **Smooth Animations** - Scroll fade-in, card hover, floating animations
- **Responsive Layout** - Perfect adaptation for desktop, tablet, and mobile devices
- **Visual Consistency** - Unified color system and spacing standards

### 🛠️ Technical Implementation
- **Lightweight Architecture** - No build tools required, runs directly in browser
- **Modular CSS** - Independent style files for easy maintenance and extension
- **Pure JavaScript** - No framework dependencies, excellent performance
- **SEO Optimized** - Complete meta tags and semantic HTML structure
- **Multilingual Support** - Built-in Chinese-English bilingual switching

### 🌐 Functional Modules
1. **Navigation Bar** - Responsive navigation with scroll effects and mobile menu
2. **Hero Section** - Brand showcase, statistics, interactive dashboard
3. **Products & Services** - 9 core product cards display
4. **Core Advantages** - Technical visualization and 4 major advantages
5. **Typical Cases** - 5 actual case studies display
6. **About Us** - Company profile, development timeline
7. **Contact Form** - Complete inquiry form and contact information
8. **Footer** - Quick links and copyright information

## 📁 Project Structure

```
webstie/
├── index.html              # Main page file
├── css/
│   ├── style.css           # Main stylesheet
│   └── i18n.css          # Internationalization styles
├── js/
│   ├── script.js           # Core scripts
│   └── i18n.js            # Internationalization support
├── renatte_icon.png        # Logo (PNG format)
├── renatte_icon.webp       # Logo (WebP optimized format)
├── optimize_images.bat      # Image optimization script
├── README.md              # Project documentation (Chinese)
├── README.en.md           # Project documentation (English)
└── LICENSE                # Open source license
```

## 🚀 Quick Start

### Local Development

1. **Clone Project**
   ```bash
   git clone https://github.com/your-username/webstie.git
   cd webstie
   ```

2. **Open Directly**
   - Double click `index.html` file
   - Or use any HTTP server (like VS Code Live Server)
   ```bash
   # Using Python
   python -m http.server 8000
   
   # Using Node.js
   npx serve
   
   # Using VS Code extension
   # Install "Live Server" extension, right-click and select "Open with Live Server"
   ```

3. **Access Website**
   - Visit `http://localhost:8000` in browser

### Production Deployment

#### Method 1: Static Hosting Platforms
- **GitHub Pages** - Free hosting with automatic CI/CD
- **Vercel** - Global CDN, zero-configuration deployment
- **Netlify** - Drag-and-drop deployment, automatic HTTPS

#### Method 2: Traditional Server
```bash
# Upload files to server
scp -r * user@your-server.com:/var/www/html

# Or use FTP tools
```

#### Method 3: Cloud Service Integration
Project is ready for deployment on:
- **Tencent Cloud EdgeOne Pages** - Frontend static hosting
- **Tencent Cloud CloudBase** - Full-stack cloud development
- **Alibaba Cloud OSS** - Object storage + CDN

## 🎯 Feature Details

### Multilingual Support

Website has complete Chinese-English bilingual support:
- Auto-detect browser language
- Manual language switching (top-right button)
- Language preference local storage
- SEO-friendly URL structure

Usage:
```javascript
// Initialize
i18n.init();

// Switch language
i18n.setLanguage('en');  // Switch to English
i18n.setLanguage('zh');  // Switch to Chinese
```

### Image Optimization

Project uses WebP format for optimized image loading:

1. **Prepare Environment**
   - Windows: Download [cwebp](https://developers.google.com/speed/webp/docs/cwebp)
   - macOS: `brew install webp`
   - Linux: `sudo apt-get install webp`

2. **Run Optimization Script**
   ```bash
   # Windows
   optimize_images.bat
   
   # Linux/macOS
   cwebp -q 85 renatte_icon.png -o renatte_icon.webp
   ```

3. **Use picture element**
   ```html
   <picture>
     <source srcset="image.webp" type="image/webp">
     <img src="image.png" alt="description" />
   </picture>
   ```

### Form Integration

Current form is frontend simulation, to connect backend:

1. **Modify `submitForm` function in `js/script.js`**
   ```javascript
   function submitForm(e) {
     e.preventDefault();
     const formData = new FormData(e.target);
     
     // Send to backend API
     fetch('https://api.renatte.com/contact', {
       method: 'POST',
       body: formData
     })
     .then(response => response.json())
     .then(data => {
       // Handle success response
       showSuccessMessage();
     })
     .catch(error => {
       // Handle error
       showErrorMessage();
     });
   }
   ```

2. **Backend API Recommendations**
   - Email Service: SendGrid / Alibaba Cloud Email Push
   - CRM Integration: XiaoYun Sales / FenXiaoKe
   - Form Service: Formspree / Netlify Forms

## 🎨 Customization

### Modify Brand Colors

Edit CSS variables in `css/style.css`:
```css
:root {
  --rose-brand: #C0175B;    /* Primary brand color */
  --rose-light: #E8417D;    /* Light brand color */
  --rose-dark: #8C0F42;     /* Dark brand color */
  --navy: #0F172A;          /* Dark color scheme */
  --muted: #64748B;         /* Gray color scheme */
}
```

### Add New Language

Add new language translation in `js/i18n.js`:
```javascript
translations: {
  zh: { /* Chinese translations */ },
  en: { /* English translations */ },
  ja: { /* Add Japanese */ }  // New language
}
```

## 🔧 Development Tools

| Tool | Purpose | Recommended Version |
|------|---------|-------------------|
| VS Code | Code Editor | Latest |
| Live Server | Local Development Server | 5.7+ |
| Chrome DevTools | Debugging | Built-in |
| Prettier | Code Formatting | 3.0+ |
| ESLint | Code Linting | 8.0+ |

## 📊 Performance Optimization Recommendations

### Implemented Optimizations
- ✅ CSS extraction to independent files
- ✅ JavaScript modularization
- ✅ WebP image format
- ✅ CDN-loaded Tailwind CSS
- ✅ Semantic HTML tags
- ✅ Lazy loading animations

### Further Optimizations
- [ ] Enable Gzip compression
- [ ] Configure CDN acceleration
- [ ] Implement image lazy loading
- [ ] Add Service Worker caching
- [ ] Preload critical resources
- [ ] Implement code splitting

## 🌐 Browser Compatibility

| Browser | Version Requirement |
|---------|-------------------|
| Chrome | 90+ |
| Firefox | 88+ |
| Safari | 14+ |
| Edge | 90+ |
| Opera | 76+ |

IE browser not supported.

## 📝 Todo List

- [ ] Add dark mode
- [ ] Implement Server-Side Rendering (SSR)
- [ ] Add unit tests
- [ ] Integrate actual form API
- [ ] Add blog/news module
- [ ] Implement web analytics (Google Analytics)
- [ ] PWA support
- [ ] Multi-language SEO optimization

## 🤝 Contributing

Contributions are welcome! Please follow these steps:

1. Fork this repository
2. Create feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to branch (`git push origin feature/AmazingFeature`)
5. Open Pull Request

### Code Standards
- Use 2-space indentation
- Follow existing naming conventions
- Add necessary comments
- Ensure browser compatibility

## 📄 Open Source License

This project is licensed under the [Academic Free License v3.0](LICENSE).

## 📞 Contact Information

- **Company Address**: No. 69 Yayun Road, Yongshang Village, Yaxi Street, Gaochun District, Nanjing, Jiangsu
- **Official Website**: https://www.renatte.com
- **Business Email**: info@renatte.com

## 🙏 Acknowledgments

Thanks to the following open source projects:
- [Tailwind CSS](https://tailwindcss.com) - CSS framework
- [Google Fonts](https://fonts.google.com) - Font service
- [Lucide](https://lucide.dev) - Icon library

---

**Nanjing Renatte Intelligent Technology Co., Ltd.** © 2026. All rights reserved.
