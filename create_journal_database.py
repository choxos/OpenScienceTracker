#!/usr/bin/env python3
"""
Script to create a comprehensive journal database from NLM Broad Subject Terms files.
This script parses all .txt files in the 'Broad Subject Terms for Indexed Journals' directory
and creates a structured database of journals with their metadata.
"""

import os
import re
import pandas as pd
import glob
from typing import Dict, List, Any


def parse_journal_entry(entry_text: str, subject_term: str) -> Dict[str, Any]:
    """
    Parse a single journal entry from the NLM format.

    Args:
        entry_text: Raw text of a journal entry
        subject_term: The broad subject term category

    Returns:
        Dictionary with parsed journal information
    """
    journal_data = {
        "broad_subject_term": subject_term,
        "nlm_id": None,
        "title_abbreviation": None,
        "title_full": None,
        "authors": None,
        "publication_start_year": None,
        "publication_end_year": None,
        "frequency": None,
        "country": None,
        "publisher": None,
        "language": None,
        "issn_electronic": None,
        "issn_print": None,
        "issn_linking": None,
        "lccn": None,
        "electronic_links": None,
        "indexing_status": None,
        "current_subset": None,
        "mesh_terms": None,
        "publication_types": None,
        "notes": None,
    }

    lines = entry_text.strip().split("\n")

    for line in lines:
        line = line.strip()

        # Parse different fields using regex patterns
        if line.startswith("Author(s):"):
            journal_data["authors"] = line.replace("Author(s):", "").strip()
        elif line.startswith("Title Abbreviation:"):
            journal_data["title_abbreviation"] = line.replace(
                "Title Abbreviation:", ""
            ).strip()
        elif line.startswith("Title(s):"):
            journal_data["title_full"] = line.replace("Title(s):", "").strip()
        elif line.startswith("Publication Start Year:"):
            year_text = line.replace("Publication Start Year:", "").strip()
            if year_text and year_text != "":
                try:
                    journal_data["publication_start_year"] = int(year_text)
                except ValueError:
                    journal_data["publication_start_year"] = year_text
        elif line.startswith("Publication End Year:"):
            year_text = line.replace("Publication End Year:", "").strip()
            if year_text and year_text != "":
                try:
                    journal_data["publication_end_year"] = int(year_text)
                except ValueError:
                    journal_data["publication_end_year"] = year_text
        elif line.startswith("Frequency:"):
            journal_data["frequency"] = line.replace("Frequency:", "").strip()
        elif line.startswith("Country of Publication:"):
            journal_data["country"] = line.replace(
                "Country of Publication:", ""
            ).strip()
        elif line.startswith("Publisher:"):
            journal_data["publisher"] = line.replace("Publisher:", "").strip()
        elif line.startswith("Language:"):
            journal_data["language"] = line.replace("Language:", "").strip()
        elif line.startswith("ISSN:"):
            issn_text = line.replace("ISSN:", "").strip()
            # Parse different ISSN types
            if "Electronic" in issn_text:
                electronic_match = re.search(r"(\d{4}-\d{4})\(Electronic\)", issn_text)
                if electronic_match:
                    journal_data["issn_electronic"] = electronic_match.group(1)
            if "Print" in issn_text:
                print_match = re.search(r"(\d{4}-\d{4})\(Print\)", issn_text)
                if print_match:
                    journal_data["issn_print"] = print_match.group(1)
            if "Linking" in issn_text:
                linking_match = re.search(r"(\d{4}-\d{4})\(Linking\)", issn_text)
                if linking_match:
                    journal_data["issn_linking"] = linking_match.group(1)
        elif line.startswith("LCCN:"):
            journal_data["lccn"] = line.replace("LCCN:", "").strip()
        elif line.startswith("Electronic Links:"):
            journal_data["electronic_links"] = line.replace(
                "Electronic Links:", ""
            ).strip()
        elif line.startswith("Current Indexing Status:"):
            journal_data["indexing_status"] = line.replace(
                "Current Indexing Status:", ""
            ).strip()
        elif line.startswith("Current Subset:"):
            journal_data["current_subset"] = line.replace("Current Subset:", "").strip()
        elif line.startswith("MeSH:"):
            journal_data["mesh_terms"] = line.replace("MeSH:", "").strip()
        elif line.startswith("Publication Type(s):"):
            journal_data["publication_types"] = line.replace(
                "Publication Type(s):", ""
            ).strip()
        elif line.startswith("Notes:"):
            journal_data["notes"] = line.replace("Notes:", "").strip()
        elif "NLM ID:" in line:
            nlm_match = re.search(r"NLM ID:\s*(\d+)\[Serial\]", line)
            if nlm_match:
                journal_data["nlm_id"] = nlm_match.group(1)

    return journal_data


def parse_subject_term_file(filepath: str, subject_term: str) -> List[Dict[str, Any]]:
    """
    Parse a single subject term file and extract all journal entries.

    Args:
        filepath: Path to the subject term file
        subject_term: Name of the subject term

    Returns:
        List of journal dictionaries
    """
    print(f"Processing: {subject_term}")

    with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()

    # Split content by journal entries (numbered entries)
    entries = re.split(r"\n\d+\.\s", content)

    journals = []
    for i, entry in enumerate(entries):
        if i == 0:  # Skip the first split part (before first entry)
            continue

        if entry.strip():  # Only process non-empty entries
            journal_data = parse_journal_entry(entry, subject_term)
            journals.append(journal_data)

    print(f"Found {len(journals)} journals in {subject_term}")
    return journals


def create_comprehensive_journal_database():
    """
    Create a comprehensive journal database from all Broad Subject Terms files.
    """
    broad_terms_dir = "Broad Subject Terms for Indexed Journals"

    if not os.path.exists(broad_terms_dir):
        print(f"Directory {broad_terms_dir} not found!")
        return

    # Get all .txt files in the directory
    files = glob.glob(os.path.join(broad_terms_dir, "*.txt"))
    print(f"Found {len(files)} subject term files to process")

    all_journals = []

    for filepath in files:
        # Extract subject term name from filename
        filename = os.path.basename(filepath)
        subject_term = filename.replace(".txt", "")

        try:
            journals = parse_subject_term_file(filepath, subject_term)
            all_journals.extend(journals)
        except Exception as e:
            print(f"Error processing {subject_term}: {e}")
            continue

    print(f"Total journals processed: {len(all_journals)}")

    # Create DataFrame
    df = pd.DataFrame(all_journals)

    # Handle duplicate journals across multiple subject terms
    # Group by title_abbreviation and aggregate subject terms
    print("Handling journals with multiple subject terms...")

    # Create a function to aggregate subject terms
    def aggregate_subject_terms(group):
        # Combine all subject terms for this journal
        subject_terms = group["broad_subject_term"].unique()
        subject_terms_str = "; ".join(sorted(subject_terms))

        # Take the first non-null value for other fields
        result = group.iloc[0].copy()
        result["broad_subject_terms"] = subject_terms_str
        result["subject_term_count"] = len(subject_terms)

        return result

    # Group by key identifier (title_abbreviation or title_full)
    df_grouped = (
        df.groupby(["title_abbreviation", "title_full"], dropna=False)
        .apply(aggregate_subject_terms)
        .reset_index(drop=True)
    )

    # Remove the old single subject term column
    df_grouped = df_grouped.drop("broad_subject_term", axis=1)

    print(f"After deduplication: {len(df_grouped)} unique journals")

    # Save to CSV
    output_file = "comprehensive_journal_database.csv"
    df_grouped.to_csv(output_file, index=False)
    print(f"Comprehensive journal database saved to: {output_file}")

    # Print some statistics
    print("\n=== DATABASE STATISTICS ===")
    print(f"Total unique journals: {len(df_grouped)}")
    print(
        f"Journals with multiple subject terms: {len(df_grouped[df_grouped['subject_term_count'] > 1])}"
    )
    print(f"Most common countries: {df_grouped['country'].value_counts().head()}")
    print(f"Most common languages: {df_grouped['language'].value_counts().head()}")

    # Show dental-related journals
    dental_journals = df_grouped[
        df_grouped["broad_subject_terms"].str.contains(
            "Dentistry|Orthodontics", na=False
        )
    ]
    print(f"\nDental-related journals: {len(dental_journals)}")

    return df_grouped


if __name__ == "__main__":
    comprehensive_db = create_comprehensive_journal_database()
