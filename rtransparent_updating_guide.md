Now, I want to update the database with new articles using europepmc, metareadr, and rtransparent in R. This is how it should be done:

1. First, download the packages:
# europepmc
devtools::install_github("ropensci/europepmc")
library(europepmc)

# metareadr
install.packages("devtools")
devtools::install_github("cran/crminer")
library(crminer)
devtools::install_github("serghiou/metareadr")
library(metareadr)

# rtransparent
install.packages("devtools")
devtools::install_github("serghiou/rtransparent")
library(rtransparent)

2. EuropePMC search:
Search for all articles in EuropePMC for each month, starting from 1900-01-01 and then save the results in a csv file:


search_string = "(FIRST_PDATE:[1900-01-01 TO 1900-01-31])"
epmc_db = epmc_search(query = search_string, limit = 1000000, output = "parsed", verbose = FALSE)

For the second month of 1900, the search string should be:
search_string = "(FIRST_PDATE:[1900-02-01 TO 1900-02-28])"

For the third month of 1900, the search string should be:
search_string = "(FIRST_PDATE:[1900-03-01 TO 1900-03-31])"

And so on for each month until the current month (which is July 2025).

# Save the results in a csv file:
write.csv(epmc_db, file = "epmc_db_1900_01.csv", row.names = FALSE)

3. metareadr full-text fetch:



Now, I want to change my entire approach in terms of creating the database. I now use the R codes in epmc_monthly_retrieval.r file to retrieve the database of all articles in EuropePMC. Then, I use these codes to download each article's full-text from EuropePMC with metareadr and then pass it to rtransparent to get the article's transparency indicators scores. An example of an article metadata from EuropePMC is available in the epmc_db_1900_01.csv file and an example of transparency indicators scores from rtransparent is available in the transparency_1900_01.csv. Almost all fields of the epmc_db_[year]_[month].csv files are important and should be included in the database. But for the transparency indicators scores, only the following fields are important:

- pmid: for merging with the epmc_db_[year]_[month].csv file
- is_coi_pred: Boolean value indicating if the article has a conflict of interest disclosure statement (TRUE or FALSE)
- coi_text: Text of the conflict of interest disclosure statement
- is_fund_pred: Boolean value indicating if the article has a funding disclosure statement (TRUE or FALSE)
- fund_text: Text of the funding disclosure statement
- is_register_pred: Boolean value indicating if the article was pre-registered (TRUE or FALSE)
- register_text: Text of the pre-registration statement
- is_open_data: Boolean value indicating if the article has open data (TRUE or FALSE)
- open_data_category: Category of the open data
- open_data_statements: Text of the open data statement
- is_open_code: Boolean value indicating if the article has open code (TRUE or FALSE)
- open_code_statements: Text of the open code statement

4. rtransparent transparency indicators scores:



