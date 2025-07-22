# Assessment of transparency indicators across the biomedical literature: How open is open?

**Authors:** Stylianos Serghiou, Despina G. Contopoulos-Ioannidis, Kevin W. Boyack, Nico Riedel, Joshua D. Wallach, John P. A. Ioannidis

## Abstract

Recent concerns about the reproducibility of science have led to several calls for more open and transparent research practices and for the monitoring of potential improvements over time. However, with tens of thousands of new biomedical articles published per week, manually mapping and monitoring changes in transparency is unrealistic. We present an open-source, automated approach to identify 5 indicators of transparency (data sharing, code sharing, conflicts of interest disclosures, funding disclosures, and protocol registration) and apply it across the entire open access biomedical literature of 2.75 million articles on PubMed Central (PMC).

## Transparency Indicators

The rtransparent package assesses **7 indicators** of transparency and reproducibility:

### Core Transparency Indicators (5):
1. **Data sharing** - Availability of research data in repositories or supplements
2. **Code sharing** - Availability of analysis code in repositories  
3. **Conflict of interest (COI) disclosure** - Statements about potential conflicts
4. **Funding disclosure** - Information about funding sources
5. **Protocol registration** - Registration in clinical trial databases

### Additional Indicators (2):
6. **Novelty statement** - Claims of novel findings (e.g., "first time reported")
7. **Replication component** - Validation of previous work or similar studies in different populations

## Validation Results

The algorithms were validated on 6,017 PMC articles from 2015-2019:

- **Accuracy**: >94% for all indicators
- **Specificity**: >98% for all indicators  
- **Sensitivity**: Varied by indicator (59-95%)
- **Error in prevalence estimation**: ≤3.6%

### Performance by Indicator:
- **COI disclosure**: 80% prevalence, high accuracy
- **Funding disclosure**: 84% prevalence, high accuracy
- **Protocol registration**: 4% prevalence, high accuracy
- **Data sharing**: 13% prevalence, moderate sensitivity (76%)
- **Code sharing**: 2% prevalence, lower sensitivity (59%)

## Key Findings Across 2.75M Articles

- **Data sharing**: 8.9% mentioned (estimated 14.5%)
- **Code sharing**: 1.2% mentioned (estimated 2.5%)
- **COI disclosure**: 68.6% mentioned (estimated 69.5%)
- **Funding disclosure**: 67.5% mentioned (estimated 67.9%)
- **Protocol registration**: 2.6% mentioned (estimated 2.5%)

## Methodology

The automated assessment uses natural language processing and keyword matching to identify transparency indicators in full-text articles. The approach enables large-scale monitoring of transparency practices across biomedical literature.

## Impact

This work enables creation of comprehensive databases to monitor transparency and reproducibility in science, providing essential infrastructure for the Open Science Tracker project. 