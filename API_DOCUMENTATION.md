# 🚀 Open Science Tracker REST API Documentation

## Overview

The Open Science Tracker REST API provides programmatic access to transparency and reproducibility data from medical and dental literature. This API is designed for researchers, meta-analysts, and developers who need to access large-scale transparency data for analysis.

## 🌐 Base URL

- **Production**: `https://ost.xeradb.com/api/`
- **API Version**: v1

## 📚 Quick Start

### 1. API Overview
Get basic information about the API and available endpoints:

```bash
GET https://ost.xeradb.com/api/
```

**Response:**
```json
{
  "api_info": {
    "name": "Open Science Tracker API",
    "version": "1.0.0",
    "description": "REST API for accessing transparency and reproducibility data"
  },
  "statistics": {
    "total_papers": 1108842,
    "total_journals": 11236,
    "transparency_coverage": {
      "open_data": 45231,
      "open_code": 12456,
      "conflict_of_interest": 892341
    }
  },
  "available_endpoints": {
    "papers": "https://ost.xeradb.com/api/v1/papers/",
    "journals": "https://ost.xeradb.com/api/v1/journals/",
    "documentation": "https://ost.xeradb.com/api/docs/"
  }
}
```

### 2. Interactive Documentation
Visit the interactive API documentation:
- **Swagger UI**: `https://ost.xeradb.com/api/docs/`
- **ReDoc**: `https://ost.xeradb.com/api/redoc/`

## 📄 Core Endpoints

### Papers (`/api/v1/papers/`)

Access research papers with transparency indicators and metadata.

#### List Papers
```bash
GET /api/v1/papers/
```

**Query Parameters:**
- `pub_year` - Filter by publication year
- `pub_year__gte` - Papers published after this year
- `pub_year__lte` - Papers published before this year  
- `journal` - Filter by journal ID
- `journal_name` - Filter by journal name (partial match)
- `transparency_score__gte` - Minimum transparency score (0-7)
- `has_open_data` - Filter papers with open data (true/false)
- `has_open_code` - Filter papers with open code (true/false)
- `author` - Filter by author name (partial match)
- `subject_category` - Filter by subject category
- `search` - Search in title and abstract
- `ordering` - Sort results (pub_year, -pub_year, pmid, etc.)
- `page` - Page number for pagination
- `page_size` - Number of results per page (max 100)

**Example Requests:**

```bash
# Get papers from 2023 with open data
GET /api/v1/papers/?pub_year=2023&has_open_data=true

# Get high-transparency papers (score ≥ 5)
GET /api/v1/papers/?transparency_score__gte=5

# Search for COVID-19 papers
GET /api/v1/papers/?search=covid-19

# Get papers from specific journal
GET /api/v1/papers/?journal_name=nature
```

#### Get Paper Details
```bash
GET /api/v1/papers/{pmid}/
```

**Response Example:**
```json
{
  "pmid": "34567890",
  "title": "Open science practices in COVID-19 research",
  "author_string": "Smith, J., Doe, A., Johnson, M.",
  "pub_year": 2023,
  "journal": {
    "id": 123,
    "title_abbreviation": "Nature",
    "title_full": "Nature",
    "publisher": "Nature Publishing Group",
    "country": "United Kingdom"
  },
  "transparency_score": 6,
  "transparency_indicators": {
    "open_data": true,
    "open_code": true,
    "conflict_of_interest": true,
    "funding_declaration": true,
    "registration": true,
    "reporting_guidelines": false,
    "data_sharing": true
  },
  "broad_subject_category": "Medicine",
  "doi": "10.1038/s41586-023-12345-6",
  "abstract": "This study examines...",
  "created_at": "2023-07-15T10:30:00Z"
}
```

#### Transparency Statistics
Get transparency statistics for filtered papers:

```bash
GET /api/v1/papers/transparency_stats/
```

Add any filters to get statistics for specific subsets:
```bash
# Statistics for papers from 2020-2023
GET /api/v1/papers/transparency_stats/?pub_year__gte=2020&pub_year__lte=2023
```

#### Papers by Year
Get paper count distribution by publication year:

```bash
GET /api/v1/papers/by_year/
```

### Journals (`/api/v1/journals/`)

Access journal information with transparency statistics.

#### List Journals
```bash
GET /api/v1/journals/
```

**Query Parameters:**
- `country` - Filter by country
- `publisher` - Filter by publisher name
- `min_papers` - Minimum number of papers in journal
- `subject_terms` - Filter by subject terms
- `search` - Search journal names
- `ordering` - Sort results

**Example Requests:**
```bash
# Get journals from United States
GET /api/v1/journals/?country=United States

# Get journals with at least 1000 papers
GET /api/v1/journals/?min_papers=1000

# Search for medical journals
GET /api/v1/journals/?search=medicine
```

#### Get Journal Details
```bash
GET /api/v1/journals/{id}/
```

**Response Example:**
```json
{
  "id": 123,
  "title_abbreviation": "Nature",
  "title_full": "Nature",
  "publisher": "Nature Publishing Group",
  "country": "United Kingdom",
  "paper_count": 15423,
  "avg_transparency_score": 4.2,
  "transparency_stats": {
    "total_papers": 15423,
    "open_data_percentage": 35.2,
    "open_code_percentage": 12.1,
    "coi_percentage": 89.4
  },
  "subject_areas": ["Medicine", "Biology", "Chemistry"],
  "recent_papers": [...],
  "issn_print": "0028-0836",
  "issn_electronic": "1476-4687"
}
```

#### Journal Papers
Get all papers from a specific journal:

```bash
GET /api/v1/journals/{id}/papers/
```

Can be combined with paper filters:
```bash
# Get 2023 papers from Nature with open data
GET /api/v1/journals/123/papers/?pub_year=2023&has_open_data=true
```

#### Top Publishers
Get top publishers by journal count:

```bash
GET /api/v1/journals/top_publishers/
```

### Research Fields (`/api/v1/research-fields/`)

Access research field classifications and statistics.

#### List Research Fields
```bash
GET /api/v1/research-fields/
```

#### Get Research Field Details
```bash
GET /api/v1/research-fields/{id}/
```

## 🔍 Advanced Usage Examples

### 1. Meta-Analysis Research
Get all cardiovascular research papers with transparency data:

```python
import requests

# Get papers in cardiovascular research
response = requests.get(
    'https://ost.xeradb.com/api/v1/papers/',
    params={
        'subject_category': 'cardiology',
        'pub_year__gte': 2020,
        'page_size': 100
    }
)

papers = response.json()['results']
for paper in papers:
    print(f"{paper['title']} - Transparency Score: {paper['transparency_score']}")
```

### 2. Journal Analysis
Compare transparency scores across journals:

```python
import requests

# Get all journals with transparency statistics
journals = []
page = 1
while True:
    response = requests.get(
        'https://ost.xeradb.com/api/v1/journals/',
        params={'page': page, 'min_papers': 100}
    )
    data = response.json()
    journals.extend(data['results'])
    
    if not data['next']:
        break
    page += 1

# Analyze transparency by publisher
from collections import defaultdict
publisher_stats = defaultdict(list)

for journal in journals:
    publisher_stats[journal['publisher']].append(journal['avg_transparency_score'])

# Calculate average transparency by publisher
for publisher, scores in publisher_stats.items():
    avg_score = sum(scores) / len(scores)
    print(f"{publisher}: {avg_score:.2f} average transparency score")
```

### 3. Longitudinal Transparency Trends
Track transparency improvements over time:

```python
import requests

# Get transparency statistics by year
years = range(2015, 2024)
transparency_trends = {}

for year in years:
    response = requests.get(
        'https://ost.xeradb.com/api/v1/papers/transparency_stats/',
        params={'pub_year': year}
    )
    
    stats = response.json()
    transparency_trends[year] = {
        'total_papers': stats['total_papers'],
        'open_data_rate': stats['transparency_indicators']['open_data']['percentage'],
        'open_code_rate': stats['transparency_indicators']['open_code']['percentage']
    }

# Plot trends using matplotlib or other visualization library
```

## 📊 Response Format

All API responses follow a consistent JSON format:

### List Responses
```json
{
  "count": 1108842,
  "next": "https://ost.xeradb.com/api/v1/papers/?page=2",
  "previous": null,
  "results": [...]
}
```

### Error Responses
```json
{
  "detail": "Not found.",
  "error_code": "not_found",
  "timestamp": "2023-07-15T10:30:00Z"
}
```

## 🔐 Authentication & Rate Limits

### Current Policy
- **Authentication**: Not required (open access for research)
- **Rate Limit**: 1000 requests per day per IP
- **CORS**: Enabled for all origins

### Future Authentication (Planned)
For higher rate limits, API keys will be available:
```bash
GET /api/v1/papers/
Authorization: Bearer your-api-key
```

## 📈 Pagination

All list endpoints support pagination:
- Default page size: 50 items
- Maximum page size: 100 items
- Use `page` parameter to navigate: `?page=2`
- Use `page_size` parameter to control size: `?page_size=100`

## 🔍 Filtering Best Practices

### 1. Combine Multiple Filters
```bash
# Papers from 2022-2023 in Nature journals with open data
GET /api/v1/papers/?pub_year__gte=2022&pub_year__lte=2023&journal_name=nature&has_open_data=true
```

### 2. Use Transparency Scoring
```bash
# High-quality transparent papers (score 5-7)
GET /api/v1/papers/?transparency_score__gte=5

# Medium transparency papers (score 3-4)
GET /api/v1/papers/?transparency_score__gte=3&transparency_score__lte=4
```

### 3. Search Optimization
```bash
# Search is indexed on title, abstract, and authors
GET /api/v1/papers/?search="machine learning"&pub_year__gte=2020
```

## 🛠️ Data Export

### Large Dataset Export
For large-scale analysis, use pagination:

```python
import requests
import json

def export_all_papers(filename='ost_papers.jsonl'):
    """Export all papers to JSONL format for analysis"""
    
    page = 1
    with open(filename, 'w') as f:
        while True:
            response = requests.get(
                'https://ost.xeradb.com/api/v1/papers/',
                params={'page': page, 'page_size': 100}
            )
            
            data = response.json()
            for paper in data['results']:
                f.write(json.dumps(paper) + '\n')
            
            print(f"Exported page {page} ({len(data['results'])} papers)")
            
            if not data['next']:
                break
            page += 1
    
    print(f"Export complete: {filename}")

# Usage
export_all_papers()
```

## 🔬 Research Use Cases

### 1. Transparency Meta-Analysis
```python
# Analyze transparency trends by research field
fields_analysis = {}
for field in research_fields:
    papers = get_papers_by_field(field['name'])
    transparency_scores = [p['transparency_score'] for p in papers]
    fields_analysis[field['name']] = {
        'mean_transparency': statistics.mean(transparency_scores),
        'median_transparency': statistics.median(transparency_scores),
        'paper_count': len(papers)
    }
```

### 2. Journal Impact Analysis
```python
# Compare journal transparency vs impact
for journal in high_impact_journals:
    journal_data = get_journal_details(journal['id'])
    transparency_score = journal_data['avg_transparency_score']
    paper_count = journal_data['paper_count']
    
    print(f"{journal['title']}: {transparency_score:.2f} transparency, {paper_count} papers")
```

### 3. Funding Agency Analysis
```python
# Analyze papers with funding declarations
funded_papers = get_papers(has_funding=True)
funding_transparency = analyze_transparency_by_funding(funded_papers)
```

## 🐛 Troubleshooting

### Common Issues

1. **Rate Limit Exceeded**
   ```json
   {"detail": "Request was throttled. Expected available in 3600 seconds."}
   ```
   Solution: Wait for the limit to reset or contact us for higher limits.

2. **Invalid Filter Parameters**
   ```json
   {"detail": "Invalid filter: invalid_parameter"}
   ```
   Solution: Check parameter names in this documentation.

3. **Large Result Sets**
   For very large queries, use smaller page sizes and implement pagination.

### Contact Support

- **Email**: ahmad.pub@gmail.com
- **GitHub Issues**: https://github.com/choxos/OpenScienceTracker/issues
- **Documentation Updates**: Check API documentation regularly

## 📜 Citation

When using OST API data in research, please cite:

```
Sofi-Mahmudi, A. (2024). Open Science Tracker: A Comprehensive Database 
of Transparency and Reproducibility in Medical Literature. 
Available at: https://ost.xeradb.com
```

## 🔄 API Changelog

### Version 1.0.0 (Current)
- Initial API release
- Papers, Journals, and Research Fields endpoints
- Advanced filtering and search
- Transparency statistics
- Interactive documentation

---

*Last updated: January 2025*
*For the most current API documentation, visit: https://ost.xeradb.com/api/docs/* 