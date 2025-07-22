#!/usr/bin/env python3
"""
Script to create the dental section of the Open Science Tracker (OST).
This script integrates the existing dental transparency data with the comprehensive
journal database to create a complete dental transparency database.
"""

import pandas as pd
import numpy as np
from datetime import datetime


def create_dental_ost_section():
    """
    Create the dental section of the OST by combining dental transparency data
    with the comprehensive journal database.
    """
    print("Creating Dental Section of Open Science Tracker...")

    # Load the comprehensive journal database
    print("Loading comprehensive journal database...")
    journals_db = pd.read_csv("comprehensive_journal_database.csv")

    # Filter for dental-related journals (Dentistry and Orthodontics)
    dental_journals = journals_db[
        journals_db["broad_subject_terms"].str.contains(
            "Dentistry|Orthodontics", na=False
        )
    ].copy()

    print(f"Found {len(dental_journals)} dental-related journals in the database")

    # Load the existing dental transparency data
    print("Loading existing dental transparency data...")
    dental_papers = pd.read_csv(
        "papers/dental_transparency_data_codes/data/dental_transparency_opendata.csv"
    )

    print(f"Found {len(dental_papers)} dental transparency papers")

    # Load journal information from the original dental study
    dental_journals_orig = pd.read_csv(
        "papers/dental_transparency_data_codes/data/dental_transparency_journals.csv"
    )

    print(f"Found {len(dental_journals_orig)} journals in original dental study")

    # Create a mapping between the original dental data and the comprehensive journal database
    print("Creating journal mapping...")

    # Match journals by abbreviation/title
    dental_papers_enhanced = dental_papers.copy()

    # Map journal information from comprehensive database
    journal_mapping = {}
    for _, journal in dental_journals.iterrows():
        # Try to match by title abbreviation
        if pd.notna(journal["title_abbreviation"]):
            journal_mapping[journal["title_abbreviation"]] = journal

    # Add enhanced journal information to dental papers
    dental_papers_enhanced["journal_nlm_id"] = None
    dental_papers_enhanced["journal_country"] = None
    dental_papers_enhanced["journal_publisher"] = None
    dental_papers_enhanced["journal_language"] = None
    dental_papers_enhanced["journal_issn_electronic"] = None
    dental_papers_enhanced["journal_issn_print"] = None
    dental_papers_enhanced["journal_broad_subject_terms"] = None
    dental_papers_enhanced["journal_mesh_terms"] = None
    dental_papers_enhanced["journal_indexing_status"] = None

    # Map journal information
    for idx, paper in dental_papers_enhanced.iterrows():
        journal_title = paper["journalTitle"]
        if journal_title in journal_mapping:
            journal_info = journal_mapping[journal_title]
            dental_papers_enhanced.at[idx, "journal_nlm_id"] = journal_info["nlm_id"]
            dental_papers_enhanced.at[idx, "journal_country"] = journal_info["country"]
            dental_papers_enhanced.at[idx, "journal_publisher"] = journal_info[
                "publisher"
            ]
            dental_papers_enhanced.at[idx, "journal_language"] = journal_info[
                "language"
            ]
            dental_papers_enhanced.at[idx, "journal_issn_electronic"] = journal_info[
                "issn_electronic"
            ]
            dental_papers_enhanced.at[idx, "journal_issn_print"] = journal_info[
                "issn_print"
            ]
            dental_papers_enhanced.at[idx, "journal_broad_subject_terms"] = (
                journal_info["broad_subject_terms"]
            )
            dental_papers_enhanced.at[idx, "journal_mesh_terms"] = journal_info[
                "mesh_terms"
            ]
            dental_papers_enhanced.at[idx, "journal_indexing_status"] = journal_info[
                "indexing_status"
            ]

    # Add the new transparency indicators: replication and novelty
    print("Adding additional transparency indicators...")

    # For now, set these as null - they would need to be assessed using rtransparent
    dental_papers_enhanced["is_replication"] = None
    dental_papers_enhanced["is_novelty"] = None
    dental_papers_enhanced["disc_replication"] = None
    dental_papers_enhanced["disc_novelty"] = None

    # Create a comprehensive transparency score
    def calculate_transparency_score(row):
        """Calculate a transparency score based on 7 indicators"""
        score = 0
        indicators = [
            "is_open_data",
            "is_open_code",
            "is_coi_pred",
            "is_fund_pred",
            "is_register_pred",
        ]
        # For now, only use the 5 available indicators
        for indicator in indicators:
            if pd.notna(row[indicator]) and row[indicator] == True:
                score += 1

        # Future: add replication and novelty when available
        # if pd.notna(row['is_replication']) and row['is_replication'] == True:
        #     score += 1
        # if pd.notna(row['is_novelty']) and row['is_novelty'] == True:
        #     score += 1

        return score

    dental_papers_enhanced["transparency_score"] = dental_papers_enhanced.apply(
        calculate_transparency_score, axis=1
    )

    # Calculate transparency score as percentage
    dental_papers_enhanced["transparency_score_pct"] = (
        dental_papers_enhanced["transparency_score"] / 5 * 100
    )  # Out of 5 indicators currently available

    # Add metadata about the assessment
    dental_papers_enhanced["assessment_date"] = datetime.now().isoformat()
    dental_papers_enhanced["assessment_tool"] = "rtransparent"
    dental_papers_enhanced["ost_version"] = "1.0"

    # Save the enhanced dental database
    output_file = "dental_ost_database.csv"
    dental_papers_enhanced.to_csv(output_file, index=False)
    print(f"Dental OST database saved to: {output_file}")

    # Create a summary statistics report
    print("\n=== DENTAL OST STATISTICS ===")
    print(f"Total dental papers: {len(dental_papers_enhanced)}")
    print(
        f"Papers with journal information mapped: {dental_papers_enhanced['journal_nlm_id'].notna().sum()}"
    )

    # Transparency indicators statistics
    print("\n--- Transparency Indicators ---")
    indicators = {
        "Data sharing": "is_open_data",
        "Code sharing": "is_open_code",
        "COI disclosure": "is_coi_pred",
        "Funding disclosure": "is_fund_pred",
        "Protocol registration": "is_register_pred",
    }

    for name, col in indicators.items():
        count = dental_papers_enhanced[col].sum()
        percentage = (count / len(dental_papers_enhanced)) * 100
        print(f"{name}: {count} ({percentage:.1f}%)")

    print(
        f"\nMean transparency score: {dental_papers_enhanced['transparency_score'].mean():.2f}/5"
    )
    print(
        f"Mean transparency percentage: {dental_papers_enhanced['transparency_score_pct'].mean():.1f}%"
    )

    # Journal statistics
    print("\n--- Journal Statistics ---")
    print("Top 10 journals by paper count:")
    journal_counts = dental_papers_enhanced["journalTitle"].value_counts().head(10)
    print(journal_counts)

    print("\nJournals by country:")
    country_counts = dental_papers_enhanced["journal_country"].value_counts().head(10)
    print(country_counts)

    print("\nJournals by publisher:")
    publisher_counts = (
        dental_papers_enhanced["journal_publisher"].value_counts().head(10)
    )
    print(publisher_counts)

    # Temporal analysis
    print("\n--- Temporal Analysis ---")
    print("Papers by year:")
    year_counts = dental_papers_enhanced["pubYear_modified"].value_counts().sort_index()
    print(year_counts)

    # Save dental journals list for future use
    dental_journals_ost = dental_journals.copy()
    dental_journals_ost.to_csv("dental_journals_ost.csv", index=False)
    print(f"\nDental journals database saved to: dental_journals_ost.csv")

    return dental_papers_enhanced, dental_journals_ost


if __name__ == "__main__":
    dental_papers, dental_journals = create_dental_ost_section()
