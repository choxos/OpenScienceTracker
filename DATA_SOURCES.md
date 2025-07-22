# 📊 Data Sources for Open Science Tracker

## Overview

The Open Science Tracker integrates multiple data sources to provide comprehensive transparency assessments across medical and dental research literature.

## 🏥 Medical Transparency Data

### Source Information
- **Repository:** Open Science Framework (OSF)
- **URL:** [https://osf.io/zbc6p/files/osfstorage/66113e60c0539424e0b4d499](https://osf.io/zbc6p/files/osfstorage/66113e60c0539424e0b4d499)
- **File:** `medicaltransparency_opendata.csv`
- **Size:** 2.5+ GB
- **Records:** ~2.7 million medical research papers
- **Assessment Tool:** rtransparent package

### Data Description
This dataset contains comprehensive transparency assessments for medical research papers, including:

#### Core Transparency Indicators
- **Open Data Sharing** - Availability of research data
- **Open Code Sharing** - Availability of analysis code
- **Conflict of Interest Disclosure** - COI statement presence
- **Funding Disclosure** - Funding source transparency
- **Protocol Registration** - Pre-registration of study protocols

#### Metadata Fields
- **Bibliographic Information** - PMID, DOI, title, authors, journal
- **Publication Details** - Year, volume, issue, pages
- **Europe PMC Data** - Open access status, PMC availability, PDF access
- **Journal Information** - ISSN, publisher, subject classification

### Assessment Methodology
- **Tool:** rtransparent R package (Serghiou et al., 2021)
- **Approach:** Automated text analysis of full-text articles
- **Validation:** >94% accuracy on transparency indicator detection
- **Coverage:** Medical literature across all specialties

## 🦷 Dental Transparency Data

### Source Information
- **Origin:** Sofi-Mahmudi et al. dental transparency research
- **Method:** Manual assessment using rtransparent protocols
- **Coverage:** Dental and orthodontic literature
- **Records:** ~10,600 dental research papers

### Assessment Scope
- **Journals:** 885+ dental and orthodontic journals
- **Time Period:** Multiple years of dental research
- **Quality Control:** Manual validation of transparency indicators
- **Specialization:** Focus on dental research transparency

## 📚 Journal Database

### Source Information
- **Origin:** National Library of Medicine (NLM) Broad Subject Terms
- **Coverage:** 11,790+ indexed journals
- **Classification:** Medical specialty categorization
- **Metadata:** Complete bibliographic and indexing information

### Journal Metadata
- **Identifiers** - NLM ID, ISSN (electronic, print, linking)
- **Bibliographic Data** - Full title, abbreviation, publisher
- **Classification** - Broad subject terms, MeSH categories
- **Publication Info** - Country, language, frequency
- **Indexing Status** - MEDLINE, PMC, and other database inclusion

## 🔗 Data Integration

### Journal Matching Strategy
1. **Primary Matching** - ISSN-based (electronic, print, linking)
2. **Secondary Matching** - Journal name matching (exact and partial)
3. **Subject Assignment** - Automatic categorization using NLM Broad Subject Terms
4. **Quality Control** - Only papers with matched journals are included

### Data Processing Pipeline
1. **Journal Database Import** - Load comprehensive journal metadata
2. **Medical Data Processing** - Import transparency assessments in chunks
3. **Dental Data Integration** - Merge existing dental transparency data
4. **Validation** - Verify data integrity and completeness
5. **Export** - Generate Railway-ready JSON exports

## 🎯 Data Quality Assurance

### Validation Steps
- **Duplicate Detection** - PMID-based deduplication
- **Journal Verification** - ISSN and name validation
- **Data Completeness** - Required field validation
- **Transparency Scoring** - Consistent calculation across datasets

### Quality Metrics
- **Journal Match Rate** - Typically 60-80% for medical data
- **Data Completeness** - >95% for core fields
- **Assessment Accuracy** - >94% for transparency indicators
- **Coverage** - Comprehensive across medical specialties

## 📖 Citation and Attribution

### Medical Transparency Data
When using the medical transparency dataset, please cite:
- The OSF repository: [https://osf.io/zbc6p/](https://osf.io/zbc6p/)
- Original rtransparent methodology: Serghiou et al. (2021)

### Dental Transparency Data
When using the dental transparency dataset, please cite:
- Sofi-Mahmudi et al. dental transparency research
- rtransparent package validation work

### Open Science Tracker Platform
When using the OST platform, please cite:
- This repository: Open Science Tracker
- Integration methodology developed for comprehensive transparency tracking

## 🔄 Data Updates

### Update Process
- **Medical Data** - Periodic updates from OSF repository
- **Journal Database** - Regular updates from NLM sources
- **Dental Data** - Ongoing assessments and additions
- **Platform Data** - Export/import capabilities for deployment

### Reproducibility
- **Version Control** - Data export timestamps and manifests
- **Processing Scripts** - Complete import/export pipeline
- **Documentation** - Comprehensive methodology documentation
- **Validation** - Automated quality checks and reporting

## 🛠️ Technical Implementation

### File Formats
- **CSV** - Raw data import/export
- **JSON** - Structured data for database import
- **Database** - PostgreSQL for production, SQLite for development

### Processing Capabilities
- **Large File Handling** - Chunked processing for 2.5+ GB files
- **Memory Efficiency** - Optimized for limited memory environments
- **Error Handling** - Robust validation and error recovery
- **Progress Tracking** - Real-time import monitoring

### Performance
- **Import Speed** - ~12,000 papers/minute
- **Database Scaling** - Supports millions of records
- **Query Performance** - Optimized indexing and relationships
- **Export Efficiency** - Chunked export for large datasets

---

## 📞 Contact and Support

For questions about data sources, processing, or integration:
- **OST Issues** - GitHub repository issues
- **Data Questions** - Contact original data authors
- **Technical Support** - OST documentation and guides

This comprehensive data integration enables the Open Science Tracker to provide unprecedented insights into research transparency across medical and dental literature. 