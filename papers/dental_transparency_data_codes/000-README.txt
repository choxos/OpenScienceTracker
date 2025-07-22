README


DESCRIPTION
These files contain the data and the research script about transparency in research articles published in dental journals

=============
CONTACT
Eero Raittio, eero.raittio@uef.fi

=============
FILES

01-Codebook.xlsx
Contains codebook of datasets included in 02-data.zip

02-data.zip
Datasets to reproduce our results.

03-dataset-creation.R
R-script to create a dataset (however, you cannot make identical dataset because more open access articles are available from the database with delay).

04-analysis.html
Supplementary material for article, showing additional results and showing R-script.

05-type-of-study-identification-code.R
R-script to reproduce type of study categorization and validation. (you have to download articles from the database with 03-dataset-creation.R)

06-r-code-for-analyses.Rmd
R-script to reproduce results and 04-analysis.html
 
=============
PREREQUISITES

To reproduce results with our data
1. Install the pacman package in R
2. Download and unpack 02-data.zip to R working directory and rename it as "data"
3. You can skip dataset creation and just run 06-r-code-for-analyses.Rmd
4. If you want to reproduce the results related to Journal Impact Factors, contact to Eero Raittio (eero.raittio@uef.fi)

To reproduce results with data you have downloaded yourself (the sample will not be identical because more open access articles are available from the database with delay); Dataset creation can take many days depending on your software.
1. Install the pacman package in R
2. Create a folder to R working directory called "pmc" where to download xml-format articles from the Europe Pubmed Central database.
3. Create a folder to R working directory called "data" where to save data you generate
4. If you want to reproduce the results related to Journal Impact Factors, contact to Eero Raittio (eero.raittio@uef.fi)

=============
SOFTWARE USED

R version 4.1.2 (2021-11-01)
Platform: x86_64-w64-mingw32/x64 (64-bit)
Running under: Windows 10 x64 (build 22000)

Matrix products: default

