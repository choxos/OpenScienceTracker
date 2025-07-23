I want to create a comprehensive database for open science called Open Science Tracker (OST). I am meta-researcher with a focus on open science. Previously, I have conducted research to assess the adherence to of medical and dental papers to open science practices. You can find some instances of my research projects in papers folder. Convert them to .md files if you cannot read PDF.

My papers used a package called rtransparent (https://github.com/serghiou/rtransparent). This package was validated in a paper that I have put in the papers folder with the name "rtransparent_validation.pdf". This package measures 5 indicators of transparency: 1) Conflict of interest disclosure, 2) Funding disclosure, 3) Data availability, 4) Code availability, 5) Pre-registration. For knowing how the package works, you can see the data and codes for my dental_transparency.pdf paper in papers/dental_transparency_data_codes.

I also want to add 6) Replication and 7) Novelty, just like the rtransparent_validation.pdf.


Now, for creating the OST:

1. First, read the papers and data and codes in papers folder.
2. Then, based on the NLM's Broad Subject Terms for Indexed Journals, create a database of journals. I have previously downloaded each broad subject term in Broad Subject Terms for Indexed Journals. I want to have a database that has every variable mentioned in the Broad Subject Terms for Indexed Journals files. Some journals may have multiple broad subject terms. Be careful about that and adjust (like have more than 1 column for the broad subject terms or use subject terms in a column but accept having more than 1 by dividing the subject terms with a semicolon).
3. Then, start with the dental section of the OST. Dentistry in in 2 broad subject terms: Dentistry and Orthodontics. Use our previous database in papers/dental_transparency_data_codes/dental_transparency_opendata.csv to create a database of dental journals.
4. Then, create a Python based website using Django. This website should have login and signup. The users can see all the the assessed papers. Also, they can see the statistics of the database. To have an insight of the kind of stats, read the papers and implement those statistics with statistical tests to compare different categories of papers.

I will send you next steps after you have completed the above steps.




I want to have the statistics based on the category. Use subject term categories for that. For example, all papers from a dental journal will be categorised as dental. You can link the subject term database with the current database using ISSN. Here is how:

1. In papers/dental_transparency_data_codes/data/dental_transparency_db.csv, you can see the output of search in europepmc (using europepmc package in R). To have correct publication type and ISSNs, connect this dental_transparency_db.csv with the current database using pmid or pmcid of papers. Then, use journalTitle, issue, pageInfo, journalVolume, pubType, isOpenAccess, inEPMC, inPMC, journalIssn, firstPublicationDate, and hasPDF from it and add them to the current database.

2. Match the ISSNs that you added to the current database with the ISSNs in the subject term database. Then, you can see the broad subject terms for each journal.

3. Show all these variables on the website for each paper: issue, pageInfo, journalVolume, pubType, isOpenAccess, inEPMC, inPMC, journalIssn, firstPublicationDate, and hasPDF. Also, based on isOpenAccess, add another indicator called "Open Access".

4. Add categories to statistics page and research fields page.



For medical transparency, project, I created a very large database (2.69 GB). Now, I want to add these papers to the OST. Add each one that its journal is available in the subject term database (match by ISSN or name). The path to the database is: papers/medicaltransparency_opendata.csv