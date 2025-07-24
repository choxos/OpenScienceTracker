# Load required libraries
library(devtools)
library(dplyr)

# Install and load packages (only run once)
# europepmc
devtools::install_github("ropensci/europepmc")
library(europepmc)

# metareadr
devtools::install_github("cran/crminer")
library(crminer)
devtools::install_github("serghiou/metareadr")
library(metareadr)

# rtransparent
devtools::install_github("serghiou/rtransparent")
library(rtransparent)

# Create output directories
raw_data_dir <- "epmc_monthly_data"
transparency_dir <- "transparency_results"
combined_dir <- "combined_monthly_results"

for(dir in c(raw_data_dir, transparency_dir, combined_dir)) {
  if (!dir.exists(dir)) {
    dir.create(dir)
  }
}

# Function to get the last day of a month
get_last_day <- function(year, month) {
  if (month == 12) {
    next_month_first <- as.Date(paste0(year + 1, "-01-01"))
  } else {
    next_month_first <- as.Date(paste0(year, "-", sprintf("%02d", month + 1), "-01"))
  }
  return(as.Date(next_month_first - 1))
}

# Function to process a single month for data retrieval
process_month_retrieval <- function(year, month, output_dir) {
  # Create date range for the month
  start_date <- as.Date(paste0(year, "-", sprintf("%02d", month), "-01"))
  end_date <- get_last_day(year, month)
  
  # Format dates for the search string
  start_str <- format(start_date, "%Y-%m-%d")
  end_str <- format(end_date, "%Y-%m-%d")
  
  # Create search string
  search_string <- paste0("(FIRST_PDATE:[", start_str, " TO ", end_str, "])")
  
  # Create filename
  filename <- paste0("epmc_db_", year, "_", sprintf("%02d", month), ".csv")
  filepath <- file.path(output_dir, filename)
  
  # Skip if file already exists
  if (file.exists(filepath)) {
    cat("File already exists, skipping:", filename, "\n")
    return(TRUE)
  }
  
  cat("Processing:", year, "-", sprintf("%02d", month), "...")
  
  # Try to search and handle potential errors
  tryCatch({
    epmc_db <- epmc_search(query = search_string, limit = 1000000, output = "parsed", verbose = FALSE)
    
    if (nrow(epmc_db) > 0) {
      write.csv(epmc_db, file = filepath, row.names = FALSE)
      cat(" Found", nrow(epmc_db), "records. Saved to", filename, "\n")
    } else {
      # Still create an empty file to track that this month was processed
      write.csv(data.frame(), file = filepath, row.names = FALSE)
      cat(" No records found. Created empty file", filename, "\n")
    }
    
    # Add a small delay to be respectful to the API
    Sys.sleep(1)
    
    return(TRUE)
    
  }, error = function(e) {
    cat(" ERROR:", e$message, "\n")
    
    # Log the error to a file
    error_log <- file.path(output_dir, "error_log.txt")
    error_msg <- paste0(Sys.time(), " - Error processing ", year, "-", sprintf("%02d", month), ": ", e$message, "\n")
    cat(error_msg, file = error_log, append = TRUE)
    
    return(FALSE)
  })
}

# Function to process transparency for a single paper
process_single_paper_transparency <- function(pmcid_clean, pmid, original_row, temp_dir) {
  tryCatch({
    # Set working directory to temp directory
    old_wd <- getwd()
    setwd(temp_dir)
    
    # Download the XML file
    mt_read_pmcoa(pmcid_clean)
    
    # Find the XML file
    xml_files <- dir(pattern = glob2rx("PMC*.xml"))
    
    if (length(xml_files) == 0) {
      cat("  No XML file found for PMC", pmcid_clean, "\n")
      setwd(old_wd)
      return(NULL)
    }
    
    filepath <- xml_files[1]  # Use the first XML file found
    
    # Process transparency analysis
    results_all <- rt_all_pmc(filepath)
    results_data <- rt_data_code_pmc_list(filepath, remove_ns = FALSE, specificity = "low")
    
    # Merge results with original row
    merged_result <- original_row
    
    # Add results_all data
    if (nrow(results_all) > 0) {
      # Match by pmid if available, otherwise just add the first row
      if ("pmid" %in% colnames(results_all) && pmid %in% results_all$pmid) {
        results_all_row <- results_all[results_all$pmid == pmid, ]
      } else {
        results_all_row <- results_all[1, ]
      }
      
      # Add prefix to avoid column name conflicts
      colnames(results_all_row) <- paste0("rt_all_", colnames(results_all_row))
      merged_result <- cbind(merged_result, results_all_row)
    }
    
    # Add results_data
    if (nrow(results_data) > 0) {
      # Match by pmid if available, otherwise just add the first row
      if ("pmid" %in% colnames(results_data) && pmid %in% results_data$pmid) {
        results_data_row <- results_data[results_data$pmid == pmid, ]
      } else {
        results_data_row <- results_data[1, ]
      }
      
      # Add prefix to avoid column name conflicts
      colnames(results_data_row) <- paste0("rt_data_", colnames(results_data_row))
      merged_result <- cbind(merged_result, results_data_row)
    }
    
    # Clean up XML file
    if (file.exists(filepath)) {
      file.remove(filepath)
    }
    
    setwd(old_wd)
    return(merged_result)
    
  }, error = function(e) {
    # Clean up and return to original directory
    if (exists("old_wd")) setwd(old_wd)
    
    # Try to clean up any XML files
    xml_files <- dir(temp_dir, pattern = glob2rx("PMC*.xml"), full.names = TRUE)
    if (length(xml_files) > 0) {
      try(file.remove(xml_files), silent = TRUE)
    }
    
    cat("  ERROR processing PMC", pmcid_clean, ":", e$message, "\n")
    return(NULL)
  })
}

# Function to process transparency for all papers in a monthly file
process_month_transparency <- function(year, month) {
  filename <- paste0("epmc_db_", year, "_", sprintf("%02d", month), ".csv")
  filepath <- file.path(raw_data_dir, filename)
  
  # Check if raw data file exists
  if (!file.exists(filepath)) {
    cat("Raw data file not found:", filename, "\n")
    return(FALSE)
  }
  
  # Check if transparency results already exist
  transparency_filename <- paste0("transparency_", year, "_", sprintf("%02d", month), ".csv")
  transparency_filepath <- file.path(transparency_dir, transparency_filename)
  
  if (file.exists(transparency_filepath)) {
    cat("Transparency file already exists, skipping:", transparency_filename, "\n")
    return(TRUE)
  }
  
  cat("Processing transparency for:", year, "-", sprintf("%02d", month), "\n")
  
  # Load the data
  tryCatch({
    db <- read.csv(filepath)
    
    if (nrow(db) == 0) {
      cat("  No data in file, creating empty transparency file\n")
      write.csv(data.frame(), file = transparency_filepath, row.names = FALSE)
      return(TRUE)
    }
    
    # Filter for open access papers
    db_oa <- db %>% filter(isOpenAccess == "Y")
    
    if (nrow(db_oa) == 0) {
      cat("  No open access papers found, creating empty transparency file\n")
      write.csv(data.frame(), file = transparency_filepath, row.names = FALSE)
      return(TRUE)
    }
    
    cat("  Found", nrow(db_oa), "open access papers to process\n")
    
    # Clean PMC IDs
    db_oa$pmcid_ <- gsub("PMC", "", as.character(db_oa$pmcid))
    
    # Remove rows with empty pmcid_
    db_oa <- db_oa[!is.na(db_oa$pmcid_) & db_oa$pmcid_ != "", ]
    
    if (nrow(db_oa) == 0) {
      cat("  No valid PMC IDs found\n")
      write.csv(data.frame(), file = transparency_filepath, row.names = FALSE)
      return(TRUE)
    }
    
    # Create temporary directory for XML processing
    temp_dir <- file.path(tempdir(), paste0("pmc_temp_", year, "_", month))
    if (!dir.exists(temp_dir)) {
      dir.create(temp_dir)
    }
    
    # Process each paper individually
    all_results <- list()
    successful_count <- 0
    
    for (i in 1:nrow(db_oa)) {
      cat("  Processing paper", i, "of", nrow(db_oa), "(PMC", db_oa$pmcid_[i], ")...")
      
      result <- process_single_paper_transparency(
        pmcid_clean = db_oa$pmcid_[i],
        pmid = db_oa$pmid[i],
        original_row = db_oa[i, ],
        temp_dir = temp_dir
      )
      
      if (!is.null(result)) {
        all_results[[length(all_results) + 1]] <- result
        successful_count <- successful_count + 1
        cat(" SUCCESS\n")
      } else {
        cat(" FAILED\n")
      }
      
      # Add small delay between requests
      Sys.sleep(0.5)
    }
    
    # Clean up temporary directory
    if (dir.exists(temp_dir)) {
      unlink(temp_dir, recursive = TRUE)
    }
    
    # Combine all results
    if (length(all_results) > 0) {
      # Convert list to data frame
      combined_results <- do.call(rbind, all_results)
      write.csv(combined_results, file = transparency_filepath, row.names = FALSE)
      cat("  Completed! Processed", successful_count, "papers successfully\n")
    } else {
      # Create empty file
      write.csv(data.frame(), file = transparency_filepath, row.names = FALSE)
      cat("  No papers processed successfully\n")
    }
    
    return(TRUE)
    
  }, error = function(e) {
    cat("  ERROR processing month:", e$message, "\n")
    
    # Log the error
    error_log <- file.path(transparency_dir, "transparency_error_log.txt")
    error_msg <- paste0(Sys.time(), " - Error processing transparency for ", year, "-", sprintf("%02d", month), ": ", e$message, "\n")
    cat(error_msg, file = error_log, append = TRUE)
    
    return(FALSE)
  })
}

# Main execution function
run_complete_analysis <- function(start_year = 1900, end_year = 2025, end_month = 7, 
                                  skip_retrieval = FALSE, skip_transparency = FALSE) {
  
  if (!skip_retrieval) {
    cat("=== PHASE 1: DATA RETRIEVAL ===\n")
    cat("Starting automated EPMC data retrieval from", start_year, "to", end_year, "-", sprintf("%02d", end_month), "\n\n")
    
    # Initialize counters for retrieval
    total_months_retrieval <- 0
    successful_months_retrieval <- 0
    
    # Loop through years and months for retrieval
    for (year in start_year:end_year) {
      max_month <- if (year == end_year) end_month else 12
      
      for (month in 1:max_month) {
        total_months_retrieval <- total_months_retrieval + 1
        
        success <- process_month_retrieval(year, month, raw_data_dir)
        
        if (success) {
          successful_months_retrieval <- successful_months_retrieval + 1
        }
        
        # Progress update every 12 months
        if (total_months_retrieval %% 12 == 0) {
          cat("\nRetrieval Progress Update:")
          cat("\nTotal months processed:", total_months_retrieval)
          cat("\nSuccessful:", successful_months_retrieval)
          cat("\nCurrent year:", year, "\n\n")
        }
      }
    }
    
    cat("\n=== RETRIEVAL PHASE COMPLETED ===\n")
    cat("Total months processed:", total_months_retrieval, "\n")
    cat("Successful retrievals:", successful_months_retrieval, "\n\n")
  }
  
  if (!skip_transparency) {
    cat("=== PHASE 2: TRANSPARENCY ANALYSIS ===\n")
    cat("Starting transparency analysis for retrieved data\n\n")
    
    # Initialize counters for transparency
    total_months_transparency <- 0
    successful_months_transparency <- 0
    
    # Loop through years and months for transparency analysis
    for (year in start_year:end_year) {
      max_month <- if (year == end_year) end_month else 12
      
      for (month in 1:max_month) {
        total_months_transparency <- total_months_transparency + 1
        
        success <- process_month_transparency(year, month)
        
        if (success) {
          successful_months_transparency <- successful_months_transparency + 1
        }
        
        # Progress update every 6 months (transparency takes longer)
        if (total_months_transparency %% 6 == 0) {
          cat("\nTransparency Progress Update:")
          cat("\nTotal months processed:", total_months_transparency)
          cat("\nSuccessful:", successful_months_transparency)
          cat("\nCurrent year:", year, "\n\n")
        }
      }
    }
    
    cat("\n=== TRANSPARENCY PHASE COMPLETED ===\n")
    cat("Total months processed:", total_months_transparency, "\n")
    cat("Successful transparency analyses:", successful_months_transparency, "\n\n")
  }
  
  cat("=== ANALYSIS COMPLETE ===\n")
  cat("Raw data directory:", raw_data_dir, "\n")
  cat("Transparency results directory:", transparency_dir, "\n")
  cat("Check error logs in respective directories for any issues.\n")
}

# Usage examples:
# Run complete analysis (both retrieval and transparency)
# run_complete_analysis()

# Run only retrieval phase
# run_complete_analysis(skip_transparency = TRUE)

# Run only transparency phase (assumes retrieval already done)
# run_complete_analysis(skip_retrieval = TRUE)

# Run for specific date range
# run_complete_analysis(start_year = 2020, end_year = 2025, end_month = 7)

# Start the complete analysis
cat("Starting complete EPMC analysis with transparency measurement\n")
cat("This process will take many hours to complete.\n")
cat("You can interrupt and restart - the script will skip already processed files.\n\n")

run_complete_analysis(skip_retrieval = TRUE)