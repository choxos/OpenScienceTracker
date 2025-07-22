### title: "Transparency indicators across the dentistry and oral health
### literature - Dataset creation"
### authors: Eero Raittio, Ahmad Sofi-Mahmudi, Sergio E Uribe

# Loading required packages
pacman::p_load(dplyr,
               rtransparent, 
               metareadr, 
               europepmc,
               here)


# Load the datasets
## Load International Standard Serial Numbers (ISSNs)
journals <- read.csv(here("data", "dental_transparency_journals.csv"))

## Some modifications are needed...

ISSNs <- paste0("ISSN:", journals$issn)

ISSNsQuery <- paste(ISSNs, 
                    collapse = " OR ")

## Load all open access dentistry and oral health papers indexed in PubMed 
## till the end of 2021:

db <- epmc_search(
        query = paste0(
                "'(",
                ISSNsQuery,
                ") ",
                'AND (SRC:"MED") 
    AND (LANG:"eng" OR LANG:"en" OR LANG:"us") 
    AND (FIRST_PDATE:[1900-01-01 TO 2021-12-31])
    AND (OPEN_ACCESS:y)
    AND (PUB_TYPE:"Journal Article" OR PUB_TYPE:"research-article" OR PUB_TYPE:"rapid-communication" OR PUB_TYPE:"product-review")',
                "'"
        ),
        limit = 100000 , output = "parsed"
)

### Let's see how many duplicates are there:
table(duplicated(db$pmid))

### Removing the duplicates:
db <- db %>% distinct(pmid, .keep_all = TRUE)


### Let's see the first six rows of the database:
head(db)


### Removing "PMC" from the cells
db$pmcid_ <-
        gsub("PMC", "", as.character(db$pmcid))


### Now, we make a folder for xml format articles and switch to that folder:
dir.create(file.path(dirname(getwd()), "pmc"))
setwd("pmc")

### Next, we download xmls in format accessible with rtransparent. To skip 
### errors (i.e., The metadata format 'pmc' is not supported by the item or by 
### the repository.), first define a new function:
skipping_errors <- function(x) tryCatch(mt_read_pmcoa(x), error = function(e) e)

### And then run the function for conflicts of interest disclosures, funding disclosures and protocol registration:
sapply(db$pmcid_, skipping_errors)

### Now we run rtransparent:
filepath = dir(pattern=glob2rx("PMC*.xml"))

results_table <- sapply(filepath, rt_all_pmc)

### A list is created now. We should convert this list to a dataframe:
df <- data.table::rbindlist(results_table, fill = TRUE)

### Merge data sharing results to database file:
setwd('..')
opendata = merge(db, results_table, by="pmid")

## Same for data and code sharing
results_data <- rt_data_code_pmc_list(
        filepath,
        remove_ns=F,
        specificity = "low")

opendata = merge(opendata,results_data,by="pmid")


### Take a 50-articles sample:
set.seed(1000)

article_sample <- opendata[sample(nrow(opendata), 50), ]

article_sample <- article_sample %>% select(pmid,
                                            pmcid,
                                            doi,
                                            title,
                                            authorString,
                                            journalTitle,
                                            pubYear,
                                            is_open_data,
                                            is_open_code,
                                            is_coi_pred,
                                            is_fund_pred,
                                            is_register_pred)

write.csv(article_sample, "data/dental_transparency_article_sample.csv")


## Adding paper type to the dataset
### Required packages:
library(xml2)
library(stringr)

typesofpapers_basic <- data.frame(interventional = c("^trial$",
                                                     "random",
                                                     "^clinical$",
                                                     "controlled",
                                                     "intervention",
                                                     "trial registration",
                                                     "cross-over",
                                                     "crossover",
                                                     "split-mouth",
                                                     "split mouth",
                                                     "blind",
                                                     NA,
                                                     NA,
                                                     NA,
                                                     NA,
                                                     NA,
                                                     NA,
                                                     NA,
                                                     NA,
                                                     NA),
                                  observational = c("cohort",
                                                    "epidemiologic",
                                                    "cross-sectional",
                                                    "cross sectional",
                                                    "case-control",
                                                    "case control",
                                                    "case report",
                                                    "case series",
                                                    "observational",
                                                    "longitudinal",
                                                    "retrospective",
                                                    "survey",
                                                    "questionnaire",
                                                    "qualitative",
                                                    "phenomenological",
                                                    "ethnographic",
                                                    "grounded theory",
                                                    "incidence",
                                                    "prevalence",
                                                    "daly"),
                                  laboratory = c("vitro",
                                                 "vivo",
                                                 "animal",
                                                 "laboratory",
                                                 "preclinical",
                                                 "pigs",
                                                 " pig ",
                                                 "rats",
                                                 " rat ",
                                                 "mouse",
                                                 "mice",
                                                 "rabbit",
                                                 "sheep",
                                                 "dogs",
                                                 " dog ",
                                                 "phantom",
                                                 NA,
                                                 NA,
                                                 NA,
                                                 NA),
                                  review = c("review",
                                             "overview",
                                             "meta-analysis",
                                             "meta analysis",
                                             "pubmed",
                                             "medline",
                                             "cochrane",
                                             "prospero",
                                             "studies included",
                                             NA,
                                             NA,
                                             NA,
                                             NA,
                                             NA,
                                             NA,
                                             NA,
                                             NA,
                                             NA,
                                             NA,
                                             NA)
)

typesofpapers_additional <- data.frame(interventional = c("experimental",
                                                          "before and after study",
                                                          "interrupted time series",
                                                          "factorial",
                                                          "cluster",
                                                          "parallel",
                                                          "underwent",
                                                          NA,
                                                          NA,
                                                          NA,
                                                          NA,
                                                          NA,
                                                          NA,
                                                          NA,
                                                          NA),
                                       observational = c("follow-up study",
                                                         "registry",
                                                         "prospective",
                                                         "reliability",
                                                         "secondary data analysis",
                                                         "secondary analysis",
                                                         "associat",
                                                         "correlation",
                                                         "bracketing",
                                                         "thematic",
                                                         "examination",
                                                         "analytical",
                                                         "ecologic",
                                                         "estimate",
                                                         "report of"),
                                       laboratory = c("specimen",
                                                      "cultured",
                                                      "testing machine",
                                                      "cells isolated",
                                                      "bovine",
                                                      NA,
                                                      NA,
                                                      NA,
                                                      NA,
                                                      NA,
                                                      NA,
                                                      NA,
                                                      NA,
                                                      NA,
                                                      NA),
                                       review = c("embase",
                                                  "cinahl",
                                                  "bibliograph",
                                                  "reference list",
                                                  "hand-search",
                                                  "manual search",
                                                  "data extraction",
                                                  NA,
                                                  NA,
                                                  NA,
                                                  NA,
                                                  NA,
                                                  NA,
                                                  NA,
                                                  NA))


# Taking a sample of 100 for validation
papertype_sample <- as.data.frame(matrix(NA, nrow = 100, ncol = 2))

set.seed(1230)
papers_sample <- sample(filepath, size = 100, replace = FALSE)

for (i in 1:length(papers_sample)) {
        data <- read_xml(papers_sample[i])
        
        # Extracting pmcid and put it in the first column
        pmcid <- xml_find_all(data, ".//article-id")
        pmcid <- xml_text(pmcid[1])
        papertype_sample$V1[i] <- pmcid
        
        # Extracting title
        title <- xml_find_all(data, ".//article-title")
        title <- xml_text(title[1])
        title <- tolower(title)
        title <- gsub("–", "-", title)
        title <- gsub("—", "-", title)
        
        # Extracting abstract
        abstract <- xml_find_all(data, ".//abstract")
        abstract <- xml_text(abstract)
        abstract <- tolower(abstract)
        abstract <- gsub("–", "-", abstract)
        abstract <- gsub("—", "-", abstract)
        
        # Checking whether title has any of the basic words
        if (is.element(TRUE, mapply(grepl, typesofpapers_basic$review, title))) {
                papertype_sample$V2[i] <- "review"
        } else if (is.element(TRUE, mapply(grepl, typesofpapers_basic$interventional, title))) {
                papertype_sample$V2[i] <- "interventional"
        } else if (is.element(TRUE, mapply(grepl, typesofpapers_basic$observational, title))) {
                papertype_sample$V2[i] <- "observational"
        } else if (is.element(TRUE, mapply(grepl, typesofpapers_basic$laboratory, title))) {
                papertype_sample$V2[i] <- "laboratory"
        } else {papertype_sample$V2[i] <- "other"}
        
        
        # Checking whether abstract has any of the basic words
        if (papertype_sample$V2[i] == "other") {
                if (rlang::is_empty(abstract) == FALSE) {
                        if (is.element(TRUE, mapply(grepl, typesofpapers_basic$review, abstract))) {
                                papertype_sample$V2[i] <- "review"
                        } else if (is.element(TRUE, mapply(grepl, typesofpapers_basic$observational, abstract))) {
                                papertype_sample$V2[i] <- "observational"
                        } else if (is.element(TRUE, mapply(grepl, typesofpapers_basic$laboratory, abstract))) {
                                papertype_sample$V2[i] <- "laboratory"
                        } else if (is.element(TRUE, mapply(grepl, typesofpapers_basic$interventional, abstract))) {
                                papertype_sample$V2[i] <- "interventional"
                        } else {papertype_sample$V2[i] <- "other"}
                        
                }}
        
        # Checking whether abstract has any of the additional words
        if (papertype_sample$V2[i] == "other") {
                if (rlang::is_empty(abstract) == FALSE) {
                        if (is.element(TRUE, mapply(grepl, typesofpapers_additional$review, abstract))) {
                                papertype_sample$V2[i] <- "review"
                        } else if (is.element(TRUE, mapply(grepl, typesofpapers_additional$observational, abstract))) {
                                papertype_sample$V2[i] <- "observational"
                        } else if (is.element(TRUE, mapply(grepl, typesofpapers_additional$laboratory, abstract))) {
                                papertype_sample$V2[i] <- "laboratory"
                        } else if (is.element(TRUE, mapply(grepl, typesofpapers_additional$interventional, abstract))) {
                                papertype_sample$V2[i] <- "interventional"
                        } else {papertype_sample$V2[i] <- "other"}
                }}
}


setwd("../GitHub/dental-transparency/papertype")

write.csv(papertype_sample, "papertype_sample_valid.csv")

### Read csv after manual validation:
papertype_sample_valid = read.csv2("papertype_sample_valid.csv")
table(papertype_sample_valid$predicted,papertype_sample_valid$true)



# After validation, run the code for all of the papers
papertype <- as.data.frame(matrix(NA, nrow = length(filepath), ncol = 2))

for (i in 1:length(filepath)) {
        data <- read_xml(filepath[i])
        
        # Extracting pmcid and put it in the first column
        pmcid <- xml_find_all(data, ".//article-id")
        pmcid <- xml_text(pmcid[1])
        papertype$V1[i] <- pmcid
        
        # Extracting title
        title <- xml_find_all(data, ".//article-title")
        title <- xml_text(title[1])
        title <- tolower(title)
        title <- gsub("–", "-", title)
        title <- gsub("—", "-", title)
        
        # Extracting abstract
        abstract <- xml_find_all(data, ".//abstract")
        abstract <- xml_text(abstract)
        abstract <- tolower(abstract)
        abstract <- gsub("–", "-", abstract)
        abstract <- gsub("—", "-", abstract)
        
        # Checking whether title has any of the basic words
        if (is.element(TRUE, mapply(grepl, typesofpapers_basic$review, title))) {
                papertype$V2[i] <- "review"
        } else if (is.element(TRUE, mapply(grepl, typesofpapers_basic$interventional, title))) {
                papertype$V2[i] <- "interventional"
        } else if (is.element(TRUE, mapply(grepl, typesofpapers_basic$observational, title))) {
                papertype$V2[i] <- "observational"
        } else if (is.element(TRUE, mapply(grepl, typesofpapers_basic$laboratory, title))) {
                papertype$V2[i] <- "laboratory"
        } else {papertype$V2[i] <- "other"}
        
        
        # Checking whether abstract has any of the basic words
        if (papertype$V2[i] == "other") {
                if (rlang::is_empty(abstract) == FALSE) {
                        if (is.element(TRUE, mapply(grepl, typesofpapers_basic$review, abstract))) {
                                papertype$V2[i] <- "review"
                        } else if (is.element(TRUE, mapply(grepl, typesofpapers_basic$observational, abstract))) {
                                papertype$V2[i] <- "observational"
                        } else if (is.element(TRUE, mapply(grepl, typesofpapers_basic$laboratory, abstract))) {
                                papertype$V2[i] <- "laboratory"
                        } else if (is.element(TRUE, mapply(grepl, typesofpapers_basic$interventional, abstract))) {
                                papertype$V2[i] <- "interventional"
                        } else {papertype$V2[i] <- "other"}
                        
                }}
        
        # Checking whether abstract has any of the additional words
        if (papertype$V2[i] == "other") {
                if (rlang::is_empty(abstract) == FALSE) {
                        if (is.element(TRUE, mapply(grepl, typesofpapers_additional$review, abstract))) {
                                papertype$V2[i] <- "review"
                        } else if (is.element(TRUE, mapply(grepl, typesofpapers_additional$observational, abstract))) {
                                papertype$V2[i] <- "observational"
                        } else if (is.element(TRUE, mapply(grepl, typesofpapers_additional$laboratory, abstract))) {
                                papertype$V2[i] <- "laboratory"
                        } else if (is.element(TRUE, mapply(grepl, typesofpapers_additional$interventional, abstract))) {
                                papertype$V2[i] <- "interventional"
                        } else {papertype$V2[i] <- "other"}
                }}
}


### Changing column names
colnames(papertype) <- c("pmcid", "studytype")

## Merge with opendata
opendata <- merge(opendata, papertype, by = "pmcid")

## Removing unnecessary columns and build the final dataset
opendata <- opendata %>% select(pmid,
                                pmcid,
                                doi,
                                title,
                                authorString,
                                journalTitle,
                                journalIssn,
                                jif2020,
                                publisher,
                                scimago_publisher,
                                firstPublicationDate,
                                pubYear_modified,
                                year_firstpub,
                                month_firstpub,
                                journalVolume,
                                pageInfo,
                                issue,
                                type,
                                studytype,
                                is_research,
                                is_review,
                                citedByCount,
                                is_coi_pred,
                                coi_text,
                                is_fund_pred,
                                fund_text,
                                is_register_pred,
                                register_text,
                                is_open_data,
                                open_data_category,
                                is_open_code,
                                open_data_statements,
                                open_code_statements)

write.csv(opendata, "data/dental_transparency_opendata.csv")
