#!/usr/bin/env python3
"""
NLM Journal Consolidation Script

Parses all txt files in "Broad Subject Terms for Indexed Journals" folder
and creates a consolidated CSV file with all journal information.
"""

import os
import re
import csv
import pandas as pd
from pathlib import Path

class NLMJournalParser:
    def __init__(self, input_folder="Broad Subject Terms for Indexed Journals"):
        self.input_folder = input_folder
        self.journals = []
        
    def parse_issn_field(self, issn_text):
        """Parse complex ISSN field and extract individual ISSNs"""
        issns = {
            'electronic': None,
            'print': None, 
            'linking': None
        }
        
        if not issn_text or issn_text.strip() == '':
            return issns
            
        # Pattern to match ISSN formats: NNNN-NNNN(Type)
        issn_pattern = r'(\d{4}-\d{3}[\dX])\s*\(([^)]+)\)'
        matches = re.findall(issn_pattern, issn_text)
        
        for issn, issn_type in matches:
            issn_type_lower = issn_type.lower()
            if 'electronic' in issn_type_lower or 'online' in issn_type_lower:
                issns['electronic'] = issn
            elif 'print' in issn_type_lower:
                issns['print'] = issn
            elif 'linking' in issn_type_lower:
                issns['linking'] = issn
                
        return issns
    
    def clean_field_value(self, value):
        """Clean and normalize field values"""
        if not value:
            return None
        value = value.strip()
        if value in ['', 'N/A', 'n/a', '-']:
            return None
        return value
    
    def parse_journal_entry(self, entry_text, broad_subject):
        """Parse a single journal entry"""
        lines = [line.strip() for line in entry_text.split('\n') if line.strip()]
        
        journal_data = {
            'broad_subject_term': broad_subject,
            'entry_number': None,
            'authors': None,
            'title_abbreviation': None,
            'title_full': None,
            'publication_start_year': None,
            'publication_end_year': None,
            'frequency': None,
            'country': None,
            'publisher': None,
            'description': None,
            'language': None,
            'issn_electronic': None,
            'issn_print': None,
            'issn_linking': None,
            'lccn': None,
            'electronic_links': None,
            'fully_indexed_in': None,
            'in_databases': None,
            'current_indexing_status': None,
            'current_subset': None,
            'mesh_terms': None,
            'publication_types': None,
            'notes': None,
            'nlm_id': None
        }
        
        # Parse each line
        for line in lines:
            line_lower = line.lower()
            
            # Extract entry number from first line
            if re.match(r'^\d+\.', line):
                journal_data['entry_number'] = re.match(r'^(\d+)\.', line).group(1)
                continue
                
            # Parse specific fields
            if line_lower.startswith('author(s):'):
                journal_data['authors'] = self.clean_field_value(line[10:])
            elif line_lower.startswith('title abbreviation:'):
                journal_data['title_abbreviation'] = self.clean_field_value(line[19:])
            elif line_lower.startswith('title(s):'):
                journal_data['title_full'] = self.clean_field_value(line[9:])
            elif line_lower.startswith('publication start year:'):
                year_text = self.clean_field_value(line[23:])
                if year_text and year_text.isdigit():
                    journal_data['publication_start_year'] = int(year_text)
            elif line_lower.startswith('publication end year:'):
                year_text = self.clean_field_value(line[21:])
                if year_text and year_text.isdigit():
                    journal_data['publication_end_year'] = int(year_text)
            elif line_lower.startswith('frequency:'):
                journal_data['frequency'] = self.clean_field_value(line[10:])
            elif line_lower.startswith('country of publication:'):
                journal_data['country'] = self.clean_field_value(line[23:])
            elif line_lower.startswith('publisher:'):
                journal_data['publisher'] = self.clean_field_value(line[10:])
            elif line_lower.startswith('description:'):
                journal_data['description'] = self.clean_field_value(line[12:])
            elif line_lower.startswith('language:'):
                journal_data['language'] = self.clean_field_value(line[9:])
            elif line_lower.startswith('issn:'):
                issns = self.parse_issn_field(line[5:])
                journal_data.update({
                    'issn_electronic': issns['electronic'],
                    'issn_print': issns['print'],
                    'issn_linking': issns['linking']
                })
            elif line_lower.startswith('lccn:'):
                journal_data['lccn'] = self.clean_field_value(line[5:])
            elif line_lower.startswith('electronic links:'):
                journal_data['electronic_links'] = self.clean_field_value(line[17:])
            elif line_lower.startswith('fully indexed in:'):
                journal_data['fully_indexed_in'] = self.clean_field_value(line[17:])
            elif line_lower.startswith('in:'):
                journal_data['in_databases'] = self.clean_field_value(line[3:])
            elif line_lower.startswith('current indexing status:'):
                journal_data['current_indexing_status'] = self.clean_field_value(line[24:])
            elif line_lower.startswith('current subset:'):
                journal_data['current_subset'] = self.clean_field_value(line[15:])
            elif line_lower.startswith('mesh:'):
                journal_data['mesh_terms'] = self.clean_field_value(line[5:])
            elif line_lower.startswith('publication type(s):'):
                journal_data['publication_types'] = self.clean_field_value(line[20:])
            elif line_lower.startswith('notes:'):
                journal_data['notes'] = self.clean_field_value(line[6:])
            elif line_lower.startswith('nlm id:'):
                journal_data['nlm_id'] = self.clean_field_value(line[7:])
                
        return journal_data
    
    def parse_file(self, file_path):
        """Parse a single subject term file"""
        broad_subject = Path(file_path).stem  # Get filename without extension
        
        print(f"Processing: {broad_subject}")
        
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        # Split into individual journal entries
        # Entries are separated by numbers followed by a period
        entries = re.split(r'\n(?=\d+\.)', content)
        
        file_journals = []
        for entry in entries:
            entry = entry.strip()
            if not entry or not re.match(r'^\d+\.', entry):
                continue
                
            try:
                journal_data = self.parse_journal_entry(entry, broad_subject)
                if journal_data['title_abbreviation'] or journal_data['title_full']:
                    file_journals.append(journal_data)
            except Exception as e:
                print(f"Error parsing entry in {broad_subject}: {str(e)}")
                continue
        
        print(f"  Found {len(file_journals)} journals")
        return file_journals
    
    def parse_all_files(self):
        """Parse all txt files in the input folder"""
        if not os.path.exists(self.input_folder):
            raise FileNotFoundError(f"Input folder not found: {self.input_folder}")
        
        txt_files = [f for f in os.listdir(self.input_folder) if f.endswith('.txt')]
        print(f"Found {len(txt_files)} subject term files to process")
        
        all_journals = []
        
        for txt_file in sorted(txt_files):
            file_path = os.path.join(self.input_folder, txt_file)
            try:
                journals = self.parse_file(file_path)
                all_journals.extend(journals)
            except Exception as e:
                print(f"Error processing {txt_file}: {str(e)}")
                continue
        
        self.journals = all_journals
        print(f"\nTotal journals parsed: {len(all_journals)}")
        return all_journals
    
    def save_to_csv(self, output_file="nlm_journals_consolidated.csv"):
        """Save parsed journals to CSV"""
        if not self.journals:
            print("No journals to save. Run parse_all_files() first.")
            return
        
        df = pd.DataFrame(self.journals)
        
        # Reorder columns for better readability
        column_order = [
            'broad_subject_term', 'entry_number', 'title_abbreviation', 'title_full',
            'authors', 'publisher', 'country', 'language', 
            'issn_electronic', 'issn_print', 'issn_linking',
            'publication_start_year', 'publication_end_year', 'frequency',
            'current_subset', 'mesh_terms', 'publication_types',
            'current_indexing_status', 'fully_indexed_in', 'in_databases',
            'lccn', 'nlm_id', 'electronic_links', 'description', 'notes'
        ]
        
        # Ensure all columns exist
        for col in column_order:
            if col not in df.columns:
                df[col] = None
        
        df = df[column_order]
        
        # Save to CSV
        df.to_csv(output_file, index=False, encoding='utf-8')
        print(f"Saved {len(df)} journals to {output_file}")
        
        # Print summary statistics
        print(f"\nSummary:")
        print(f"  Total journals: {len(df):,}")
        print(f"  Unique broad subject terms: {df['broad_subject_term'].nunique()}")
        print(f"  Journals with electronic ISSN: {df['issn_electronic'].notna().sum():,}")
        print(f"  Journals with print ISSN: {df['issn_print'].notna().sum():,}")
        print(f"  Journals with linking ISSN: {df['issn_linking'].notna().sum():,}")
        print(f"  Countries represented: {df['country'].nunique()}")
        
        return df

def main():
    parser = NLMJournalParser()
    journals = parser.parse_all_files()
    df = parser.save_to_csv()
    return df

if __name__ == "__main__":
    df = main() 