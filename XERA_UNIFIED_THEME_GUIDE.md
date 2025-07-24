# 🎨 Xera DB Unified Theme Implementation Guide

## Overview

This guide explains how to implement the unified theme system across all Xera DB research applications, ensuring consistent design language while maintaining each app's unique identity through distinct color schemes.

## 🌈 **Color Schemes Summary**

| Application | Primary Color | Theme | Icon | Country/Focus |
|-------------|---------------|-------|------|---------------|
| **OST** | Deep Blue `#2563eb` | Trust & Transparency | 🔬 fa-microscope | Open Science |
| **PRCT** | Crimson Red `#dc2626` | Alert & Analysis | ⚠️ fa-exclamation-triangle | Retractions |
| **CIHRPT** | Maple Red `#dc2626` | Canadian Excellence | 🇨🇦 fa-flag | Canada |
| **NHMRCPT** | Forest Green `#059669` | Australian Innovation | 🇦🇺 fa-flag | Australia |
| **NIHRPT** | Royal Blue `#1d4ed8` | British Research | 🇬🇧 fa-flag | United Kingdom |
| **NIHPT** | Navy Blue `#1e3a8a` | American Innovation | 🇺🇸 fa-flag | United States |
| **TTEdb** | Medical Purple `#7c3aed` | Clinical Excellence | 🧬 fa-flask | Clinical Trials |
| **DCPS** | Mint Green `#059669` | Health & Wellness | 🦷 fa-tooth | Dental Health |

---

## 📁 **File Structure**

```
static/css/
├── xera-unified-theme.css          # Base theme (shared across all apps)
├── ost-theme.css                   # OST-specific colors (current app)
└── themes/
    ├── prct-theme.css              # PRCT-specific colors
    ├── cihrpt-theme.css            # CIHRPT-specific colors
    ├── nhmrcpt-theme.css           # NHMRCPT-specific colors
    ├── nihrpt-theme.css            # NIHRPT-specific colors
    ├── nihpt-theme.css             # NIHPT-specific colors
    ├── ttedb-theme.css             # TTEdb-specific colors
    └── dcps-theme.css              # DCPS-specific colors

templates/
└── tracker/
    └── xera_base.html              # Unified base template
```

---

## 🚀 **Implementation Steps**

### **Step 1: Copy Base Files**

For each application, copy these files:

1. **`static/css/xera-unified-theme.css`** - Base theme system
2. **`templates/tracker/xera_base.html`** - Unified base template
3. **Appropriate theme file** from `static/css/themes/` directory

### **Step 2: Update HTML Templates**

#### **Base Template Usage**

```html
{% extends "tracker/xera_base.html" %}
{% load static %}

{% block title %}Your Page Title{% endblock %}

{% block extra_css %}
    <!-- App-specific CSS -->
    <link rel="stylesheet" href="{% static 'css/app-specific.css' %}">
{% endblock %}

{% block content %}
    <!-- Your page content -->
    <div class="xera-container">
        <div class="xera-stats-grid">
            <div class="xera-stat-card ost-stat-papers">
                <h2 class="xera-stat-number">1,234,567</h2>
                <p class="xera-stat-label">Research Papers</p>
            </div>
        </div>
    </div>
{% endblock %}
```

#### **Header Configuration**

Update the header section in the base template for each app:

```html
<!-- Example for PRCT -->
<a href="{% url 'tracker:home' %}" class="xera-logo">
    <div class="xera-logo-icon">
        <i class="fas fa-exclamation-triangle"></i>
    </div>
    <div class="xera-app-name">
        <div class="xera-app-title">PRCT</div>
        <div class="xera-app-subtitle">Post-Retraction Citation Tracker</div>
    </div>
</a>
```

### **Step 3: Update CSS Includes**

In your base template, include the appropriate theme:

```html
<!-- For OST -->
<link rel="stylesheet" href="{% static 'css/xera-unified-theme.css' %}">
<link rel="stylesheet" href="{% static 'css/ost-theme.css' %}">

<!-- For PRCT -->
<link rel="stylesheet" href="{% static 'css/xera-unified-theme.css' %}">
<link rel="stylesheet" href="{% static 'css/themes/prct-theme.css' %}">

<!-- For CIHRPT -->
<link rel="stylesheet" href="{% static 'css/xera-unified-theme.css' %}">
<link rel="stylesheet" href="{% static 'css/themes/cihrpt-theme.css' %}">

<!-- And so on... -->
```

---

## 🎨 **Theme Components Usage**

### **Statistics Cards**

```html
<div class="xera-stats-grid">
    <!-- Primary metric -->
    <div class="xera-stat-card ost-stat-papers">
        <h2 class="xera-stat-number">{{ total_papers|floatformat:0 }}</h2>
        <p class="xera-stat-label">Research Papers</p>
        <p class="xera-stat-change positive">+5.2% this month</p>
    </div>
    
    <!-- Secondary metric -->
    <div class="xera-stat-card ost-stat-journals">
        <h2 class="xera-stat-number">{{ total_journals|floatformat:0 }}</h2>
        <p class="xera-stat-label">Journals</p>
    </div>
</div>
```

### **Content Cards**

```html
<div class="xera-card">
    <div class="xera-card-header">
        <h3 class="xera-card-title">
            <i class="fas fa-chart-bar me-2"></i>
            Transparency Metrics
        </h3>
    </div>
    <div class="xera-card-body">
        <!-- Card content -->
    </div>
</div>
```

### **Buttons**

```html
<!-- Primary action -->
<a href="#" class="xera-btn xera-btn-primary">
    <i class="fas fa-search me-1"></i>Search Papers
</a>

<!-- Secondary action -->
<a href="#" class="xera-btn xera-btn-secondary">
    <i class="fas fa-download me-1"></i>Export Data
</a>

<!-- App-specific button (uses app theme) -->
<a href="#" class="xera-btn xera-btn-ost">
    <i class="fas fa-microscope me-1"></i>Analyze Transparency
</a>
```

### **Forms**

```html
<div class="ost-search-container">
    <form class="ost-filter-group">
        <div class="xera-form-group">
            <label class="xera-label">Search Term</label>
            <input type="text" class="xera-input" placeholder="Enter search term...">
        </div>
        
        <div class="xera-form-group">
            <label class="xera-label">Category</label>
            <select class="xera-select">
                <option>All Categories</option>
                <option>Medicine</option>
                <option>Dentistry</option>
            </select>
        </div>
        
        <button type="submit" class="xera-btn xera-btn-primary">Search</button>
    </form>
</div>
```

### **Tables**

```html
<div class="xera-table-container">
    <table class="xera-table" data-large-table>
        <thead>
            <tr>
                <th data-sortable data-sort-type="text">Title</th>
                <th data-sortable data-sort-type="numeric">Year</th>
                <th data-sortable data-sort-type="numeric">Transparency Score</th>
            </tr>
        </thead>
        <tbody>
            {% for paper in papers %}
            <tr>
                <td>{{ paper.title }}</td>
                <td>{{ paper.pub_year }}</td>
                <td>
                    <span class="ost-transparency-score {% if paper.transparency_score >= 6 %}high{% elif paper.transparency_score >= 3 %}medium{% else %}low{% endif %}">
                        {{ paper.transparency_score }}/7
                    </span>
                </td>
            </tr>
            {% endfor %}
        </tbody>
    </table>
</div>
```

---

## 🔧 **App-Specific Customizations**

### **PRCT (Post-Retraction Citation Tracker)**

```html
<!-- Retraction status indicators -->
<span class="prct-retraction-status retracted">
    <i class="fas fa-exclamation-triangle me-1"></i>Retracted
</span>

<!-- Citation trend indicators -->
<span class="prct-citation-trend declining">
    <i class="fas fa-arrow-down me-1"></i>Citations Declining
</span>

<!-- Alert boxes -->
<div class="xera-alert prct-alert-retraction">
    <strong>Retraction Alert:</strong> This paper has been retracted due to data fabrication.
</div>
```

### **Country-Specific Applications (CIHRPT, NHMRCPT, etc.)**

```html
<!-- Funding status indicators -->
<span class="xera-badge xera-badge-primary">
    <i class="fas fa-dollar-sign me-1"></i>Funded: $125,000 CAD
</span>

<!-- Research pillar indicators -->
<span class="xera-badge" style="background-color: var(--cihrpt-biomedical); color: white;">
    Biomedical Research
</span>
```

### **TTEdb (Target Trial Emulation)**

```html
<!-- Study methodology indicators -->
<span class="xera-badge" style="background-color: var(--ttedb-randomized); color: white;">
    Randomized Controlled Trial
</span>

<!-- Clinical trial phase -->
<span class="xera-badge" style="background-color: var(--ttedb-phase-3); color: white;">
    Phase III
</span>
```

### **DCPS (Dental Caries)**

```html
<!-- Dental health indicators -->
<span class="xera-badge" style="background-color: var(--dcps-healthy); color: white;">
    <i class="fas fa-tooth me-1"></i>Healthy
</span>

<!-- Population demographics -->
<span class="xera-badge" style="background-color: var(--dcps-children); color: white;">
    Children (5-12 years)
</span>
```

---

## 🚀 **Performance Optimizations**

### **Lazy Loading Integration**

```html
<!-- For large lists -->
<div class="xera-container" data-progressive-load data-items-per-page="20">
    {% for item in items %}
    <div class="xera-card" data-progressive-item>
        <!-- Item content -->
    </div>
    {% endfor %}
</div>

<!-- For images -->
<img data-src="{% static 'images/chart.png' %}" 
     class="lazy" 
     alt="Transparency Chart" 
     width="400" 
     height="300">
```

### **Debounced Search**

```html
<input type="text" 
       class="xera-input" 
       data-search-debounce="300"
       placeholder="Search papers...">
```

---

## 🎯 **Cross-Application Navigation**

The unified footer automatically includes navigation to all Xera DB applications:

```html
<!-- This is automatically included in xera_base.html -->
<footer class="xera-footer">
    <div class="xera-footer-apps">
        <!-- Links to all 8 applications -->
    </div>
</footer>
```

---

## 📱 **Responsive Design**

The theme includes automatic responsive adjustments:

```css
@media (max-width: 768px) {
    .xera-stats-grid {
        grid-template-columns: 1fr; /* Single column on mobile */
    }
    
    .ost-filter-group {
        flex-direction: column; /* Stack filters vertically */
    }
}
```

---

## 🔧 **Deployment Checklist**

### **For Each Application:**

- [ ] Copy `xera-unified-theme.css` to `static/css/`
- [ ] Copy appropriate theme file (e.g., `prct-theme.css`)
- [ ] Update base template to use `xera_base.html`
- [ ] Update CSS includes in templates
- [ ] Update logo icon and app name in header
- [ ] Test responsive design on mobile
- [ ] Verify cross-application footer links
- [ ] Test performance optimizations (lazy loading, etc.)
- [ ] Update navigation menu items
- [ ] Test accessibility and color contrast

### **Domain Configuration:**

Update the footer links to match your actual domain structure:

```html
<!-- Update these URLs in xera_base.html -->
<a href="https://ost.xeradb.com">OST</a>
<a href="https://prct.xeradb.com">PRCT</a>
<a href="https://cihrpt.xeradb.com">CIHRPT</a>
<!-- etc. -->
```

---

## 🎨 **Custom Theme Creation**

To create a theme for a new application:

1. **Copy a similar theme file** (e.g., `ost-theme.css`)
2. **Update CSS variables:**

```css
:root {
  /* Your Primary Colors */
  --xera-primary: #your-color;
  --xera-primary-light: #lighter-shade;
  --xera-primary-dark: #darker-shade;
  
  /* Your gradients */
  --yourapp-gradient-primary: linear-gradient(135deg, #color1 0%, #color2 100%);
}

/* Your specific styling */
.xera-header {
  background: var(--yourapp-gradient-primary);
}

.xera-logo-icon i:before {
  content: "\f000"; /* Your FontAwesome icon code */
}
```

3. **Add app-specific component styles**
4. **Update the unified footer** to include your new app

---

## 🎯 **Benefits of This System**

### **For Users:**
- **Consistent experience** across all Xera DB applications
- **Easy navigation** between different research tools
- **Professional appearance** that builds trust
- **Responsive design** that works on all devices

### **For Developers:**
- **Shared CSS codebase** reduces duplication
- **Easy theme updates** across all applications
- **Consistent component library** speeds development
- **Performance optimizations** built-in

### **For Brand:**
- **Unified Xera DB identity** across all tools
- **Professional research platform** appearance
- **Easy to expand** with new applications
- **Memorable color associations** for each tool

---

## 🚀 **Ready to Implement!**

This unified theme system transforms your 8 research applications into a cohesive, professional suite while maintaining each app's unique identity. The system is designed for easy maintenance, excellent performance, and seamless user experience across the entire Xera DB ecosystem.

**Start with OST** (already implemented) and gradually roll out to other applications using this guide! 🎨✨ 