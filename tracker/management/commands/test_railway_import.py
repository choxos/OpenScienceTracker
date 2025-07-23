from django.core.management.base import BaseCommand
import os
import pandas as pd
from tracker.models import Journal

class Command(BaseCommand):
    help = 'Test command to diagnose Railway import issues'

    def handle(self, *args, **options):
        self.stdout.write('🧪 TESTING RAILWAY IMPORT...')
        
        # Check environment
        railway_env = os.environ.get('RAILWAY_ENVIRONMENT')
        self.stdout.write(f'📍 Railway Environment: {railway_env}')
        
        if not railway_env:
            self.stdout.write(self.style.WARNING('❌ Not in Railway environment'))
            return
        
        # Check if CSV exists
        csv_exists = os.path.exists('dental_journals_ost.csv')
        self.stdout.write(f'📄 CSV exists: {csv_exists}')
        
        if csv_exists:
            # Try to read CSV
            try:
                df = pd.read_csv('dental_journals_ost.csv')
                self.stdout.write(f'📊 CSV rows: {len(df)}')
            except Exception as e:
                self.stdout.write(f'❌ CSV read error: {e}')
        
        # Check database connection
        try:
            journal_count = Journal.objects.count()
            self.stdout.write(f'🗄️ Current journals in DB: {journal_count}')
        except Exception as e:
            self.stdout.write(f'❌ DB connection error: {e}')
        
        # Check for dental journals
        try:
            dental_count = Journal.objects.filter(broad_subject_terms__icontains='Dentistry').count()
            self.stdout.write(f'🦷 Dental journals in DB: {dental_count}')
        except Exception as e:
            self.stdout.write(f'❌ Dental query error: {e}')
        
        # Test django-postgres-copy import
        try:
            from postgres_copy import CopyManager
            self.stdout.write('✅ django-postgres-copy imported successfully')
        except Exception as e:
            self.stdout.write(f'❌ django-postgres-copy import error: {e}')
        
        self.stdout.write('🧪 Test completed!') 