# 🔬 Open Science Tracker (OST)

A comprehensive web application for tracking transparency indicators across biomedical literature, built on the validated **rtransparent** methodology.

## 👨‍💼 Author

**Ahmad Sofi-Mahmudi**
- 📧 [ahmad.pub@gmail.com](mailto:ahmad.pub@gmail.com)
- 🎓 [Google Scholar](https://scholar.google.com/citations?user=gTWPaFYAAAAJ&hl=en)
- 💼 [LinkedIn](https://www.linkedin.com/in/asofimahmudi)
- 💻 [GitHub](https://github.com/choxos)
- 🐦 [X (Twitter)](https://x.com/ASofiMahmudi)

## 🌟 Overview

The Open Science Tracker (OST) promotes transparency and reproducibility in biomedical research by systematically tracking 7 key transparency indicators across scientific publications. Built specifically for meta-researchers studying open science practices, OST provides a robust platform for analyzing research transparency trends.

## 📊 Transparency Indicators

OST tracks the following evidence-based transparency indicators:

### Core Indicators (5)
1. **📊 Data Sharing** - Availability of research data in repositories or supplements
2. **💻 Code Sharing** - Availability of analysis code in repositories  
3. **⚖️ Conflict of Interest Disclosure** - Statements about potential conflicts
4. **💰 Funding Disclosure** - Information about funding sources
5. **📝 Protocol Registration** - Registration in clinical trial databases

### Additional Indicators (2) 
6. **🔄 Replication Component** - Validation of previous work or similar studies
7. **✨ Novelty Statement** - Claims of novel findings

## 🎯 Key Features

### 📋 Comprehensive Database
- **10,659+ dental research papers** with transparency assessments
- **Ready for medical transparency data** (2.69 GB dataset with journal matching)
- **885+ dental and orthodontic journals** with complete metadata
- **11,790+ total journals** from NLM Broad Subject Terms
- Integration with existing rtransparent analyses

### 🔍 Advanced Search & Analysis
- **Paper Search** - Filter by transparency indicators, journals, years
- **Journal Analysis** - Compare transparency metrics across publishers/countries
- **Statistical Dashboard** - Comprehensive transparency statistics and trends
- **Export Functionality** - CSV/Excel export for further analysis

### 🚀 REST API for Researchers
- **Programmatic Access** - Full REST API for external researchers and developers
- **Advanced Filtering** - Query papers by transparency scores, journals, years, authors
- **Bulk Data Export** - Download large datasets for meta-analysis
- **Real-time Statistics** - Get transparency statistics with custom filters
- **Interactive Documentation** - Swagger UI and ReDoc for easy API exploration
- **Research-Friendly** - Open access with generous rate limits for academic use

### 👥 User Management
- **User Authentication** - Secure login/signup system
- **Personal Profiles** - Research interests and field preferences  
- **Personalized Dashboard** - Custom views based on research areas
- **Admin Interface** - Full Django admin for data management

### 📈 Visualization & Statistics
- **Transparency Trends** - Time-series analysis of indicator adoption
- **Journal Rankings** - Performance metrics by transparency scores
- **Country/Publisher Analysis** - Geographic and institutional patterns
- **Interactive Charts** - Dynamic visualizations with Chart.js

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- pip (Python package manager)
- Git

### Installation

#### Option 1: Automated Setup (Recommended)

1. **Clone the repository**
   ```bash
   git clone https://github.com/your-username/OpenScienceTracker.git
   cd OpenScienceTracker
   ```

2. **Run the setup script**
   ```bash
   ./setup.sh
   ```

3. **Activate the virtual environment**
   ```bash
   ./activate.sh
   ```

4. **Setup database**
   ```bash
   python manage.py migrate
   ```

5. **Create admin user**
   ```bash
   python manage.py createsuperuser
   ```

6. **Run the development server**
   ```bash
   python manage.py runserver
   ```

#### Option 2: Manual Setup

1. **Clone and setup virtual environment**
   ```bash
   git clone https://github.com/your-username/OpenScienceTracker.git
   cd OpenScienceTracker
   python3 -m venv ost_env
   source ost_env/bin/activate  # On Windows: ost_env\Scripts\activate
   ```

2. **Install dependencies**
   ```bash
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

3. **Setup database and create admin user**
   ```bash
   python manage.py migrate
   python manage.py createsuperuser
   ```

4. **Run the development server**
   ```bash
   python manage.py runserver
   ```

### Access the Application
   - Web interface: http://localhost:8000
   - Admin interface: http://localhost:8000/admin

## 📁 Project Structure

```
OpenScienceTracker/
├── tracker/                    # Main Django app
│   ├── models.py              # Database models
│   ├── views.py               # View controllers
│   ├── forms.py               # Form definitions
│   ├── admin.py               # Admin interface
│   └── urls.py                # URL routing
├── templates/                  # HTML templates
│   ├── tracker/               # App-specific templates
│   └── registration/          # Authentication templates
├── static/                     # Static files (CSS, JS, images)
├── papers/                     # Research papers and data
│   └── dental_transparency_data_codes/  # Dental study data
├── Broad Subject Terms for Indexed Journals/  # NLM journal data
├── ost_web/                   # Django project settings
├── manage.py                  # Django management script
├── import_dental_data_fixed.py  # Data import script
└── comprehensive_journal_database.csv  # Journal database
```

## 📊 Current Database Statistics

### Dental Research Focus
- **10,659 research papers** analyzed for transparency
- **885 dental and orthodontic journals** 
- **Mean transparency score: 1.47/5** (29.4% of available indicators)

### Transparency Breakdown
- **COI Disclosure: 76.7%** ✅ (Excellent compliance)
- **Funding Disclosure: 61.5%** ✅ (Good compliance)  
- **Protocol Registration: 6.9%** ⚠️ (Needs improvement)
- **Data Sharing: 2.0%** 🔴 (Critical need for improvement)
- **Code Sharing: 0.1%** 🔴 (Critical need for improvement)

## 🔧 Key Components

### Models
- **Journal**: Complete journal metadata with NLM classification
- **Paper**: Research papers with transparency indicators
- **ResearchField**: Research area categorization
- **UserProfile**: Extended user profiles with preferences
- **TransparencyTrend**: Time-series analysis capability

### Data Sources
- **rtransparent package**: Validated transparency assessment tool
- **Europe PubMed Central**: Open access article database
- **NLM Broad Subject Terms**: Journal classification system
- **ScimagoJR & JCR**: Journal impact metrics

## 📈 Research Applications

### For Meta-Researchers
- Track transparency trends across disciplines
- Compare institutional and publisher policies
- Analyze effectiveness of transparency interventions
- Generate evidence for open science advocacy

### For Institutions
- Assess researcher compliance with transparency requirements
- Benchmark against peer institutions
- Monitor progress toward open science goals
- Support policy development

### For Journals & Publishers
- Evaluate editorial policy effectiveness
- Compare transparency metrics with competitors
- Identify areas for policy improvement
- Support editorial decision-making

## 🔬 Technical Details

### Built With
- **Backend**: Django 5.1, Python 3.12
- **Database**: SQLite (development), PostgreSQL (production ready)
- **Frontend**: Bootstrap 5, Chart.js, Font Awesome
- **Data Processing**: pandas, numpy
- **Assessment Tool**: rtransparent package validation

### Assessment Methodology
Based on the validated rtransparent package (Serghiou et al., 2021):
- **Automated text analysis** of full-text articles
- **Natural language processing** for indicator detection
- **Validated algorithms** with >94% accuracy
- **Standardized scoring** across publications

## 🏥 Medical Data Import

The OST supports importing large medical transparency datasets with journal matching:

### 📥 Import Process
1. **Download dataset:** Available on OSF at [https://osf.io/zbc6p/files/osfstorage/66113e60c0539424e0b4d499](https://osf.io/zbc6p/files/osfstorage/66113e60c0539424e0b4d499)
2. **Place dataset:** Save `medicaltransparency_opendata.csv` in `papers/` directory
3. **Test import:** Run `python test_medical_import.py` to validate data structure
4. **Full import:** Run `python manage.py import_medical_papers_bulk` for complete import with progress tracking
5. **Monitor progress:** Real-time statistics and progress tracking

### 🔗 Journal Matching Strategy
- **ISSN matching:** Primary method using electronic, print, and linking ISSNs
- **Name matching:** Fallback using exact and partial journal title matching
- **Subject categorization:** Automatic assignment based on NLM Broad Subject Terms
- **Only matched papers:** Papers without journal matches are skipped

### ⚡ Performance Features
- **Chunked processing:** Handles large files (2.69 GB+) without memory issues
- **Progress tracking:** Real-time statistics per chunk (10,000 rows each)
- **Duplicate detection:** Automatic PMID-based duplicate handling
- **Transaction safety:** Database integrity with atomic operations
- **Memory management:** Efficient processing for large datasets

### 📊 Expected Results
- **Journal match rate:** Typically 60-80% based on ISSN/name availability
- **Processing speed:** ~2-5 minutes per 10,000 records
- **Subject categories:** Automatic categorization across all medical fields
- **Full integration:** Seamless addition to existing OST database

## 🚀 API Documentation

For researchers and developers who need programmatic access to OST data:

### 📖 API Resources
- **📋 Full API Documentation**: [API_DOCUMENTATION.md](API_DOCUMENTATION.md)
- **🔗 Interactive API Explorer**: `https://ost.xeradb.com/api/docs/`
- **📊 API Overview**: `https://ost.xeradb.com/api/`

### ⚡ Quick API Examples

```bash
# Get transparency statistics for 2023 papers
curl "https://ost.xeradb.com/api/v1/papers/transparency_stats/?pub_year=2023"

# Search for COVID-19 papers with open data
curl "https://ost.xeradb.com/api/v1/papers/?search=covid-19&has_open_data=true"

# Get journal information with paper counts
curl "https://ost.xeradb.com/api/v1/journals/?min_papers=100"
```

### 🔬 Research Use Cases
- **Meta-analysis**: Bulk download transparency data for systematic reviews
- **Bibliometric analysis**: Analyze transparency trends across journals and fields
- **Journal comparison**: Compare transparency policies and practices
- **Temporal analysis**: Track transparency improvements over time

## 📚 Research Foundation

This project builds on published research:
- **rtransparent validation**: Serghiou et al. (2021) *PLOS Biology*
- **Dental transparency analysis**: Your dental transparency research
- **Medical transparency analysis**: Your medical transparency research

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/new-feature`)
3. Commit changes (`git commit -am 'Add new feature'`)
4. Push to branch (`git push origin feature/new-feature`)
5. Create Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 📞 Contact & Support

For questions, suggestions, or collaboration opportunities:
- **Email**: [ahmad.pub@gmail.com](mailto:ahmad.pub@gmail.com)
- **Research Profile**: [Google Scholar](https://scholar.google.com/citations?user=gTWPaFYAAAAJ&hl=en)
- **GitHub**: [choxos](https://github.com/choxos)
- **LinkedIn**: [Ahmad Sofi-Mahmudi](https://www.linkedin.com/in/asofimahmudi)
- **X (Twitter)**: [@ASofiMahmudi](https://x.com/ASofiMahmudi)

## 🙏 Acknowledgments

- **rtransparent package** authors for the validated methodology
- **Europe PubMed Central** for open access article database
- **NLM** for the Broad Subject Terms classification system
- **Open science community** for promoting research transparency

---

**📊 Promoting transparency, one paper at a time.**