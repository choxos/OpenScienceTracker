library(pacman)
p_load(dplyr,xml2,stringr)

setwd("pmc") # select path you downloaded articles in XML-format

filepath = dir(pattern=glob2rx("PMC*.xml"))

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


setwd("../GitHub/dental-transparency/papertype") #set working directory where you want to wrtie csv-file


write.csv(papertype_sample, "papertype_sample_valid.csv")
# Results from manual validation
papertype_sample_valid = read.csv2("papertype_sample_valid.csv")
table(papertype_sample_valid$predicted,papertype_sample_valid$true)

# After validation, run the code for all of the papers

setwd("pmc")

papertype <- as.data.frame(matrix(NA, nrow = length(filepath), ncol = 2))


for (i in 1:length(filepath)) {
        data <- read_xml(filepath[i])
        
        pmcid <- xml_find_all(data, ".//article-id")
        pmcid <- xml_text(pmcid[1])
        papertype$V1[i] <- pmcid
        
        
        title <- xml_find_all(data, ".//article-title")
        title <- xml_text(title[1])
        
        abstract <- xml_find_all(data, ".//abstract")
        abstract <- xml_text(abstract)
        
        titleabstract <- paste(title, abstract, sep = " ")
        
        if (is.element(TRUE, mapply(grepl, typesofpapers$interventional, titleabstract))) {
                papertype$V2[i] <- "interventional"
        } else if (is.element(TRUE, mapply(grepl, typesofpapers$observational, titleabstract))) {
                papertype$V2[i] <- "observational"
        } else if (is.element(TRUE, mapply(grepl, typesofpapers$laboratory, titleabstract))) {
                papertype$V2[i] <- "laboratory"
        } else if (is.element(TRUE, mapply(grepl, typesofpapers$review, titleabstract))) {
                papertype$V2[i] <- "review"
        } else {papertype$V2[i] <- "other"} 
        
}





