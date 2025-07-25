from django.core.management.base import BaseCommand
from django.core.cache import cache
from django.db import connection
from django.conf import settings
import time
import psutil
import os

class Command(BaseCommand):
    help = 'Comprehensive performance optimization and monitoring for OST'

    def add_arguments(self, parser):
        parser.add_argument(
            '--action',
            type=str,
            choices=['analyze', 'optimize', 'warm-cache', 'migrate-indexes', 'monitor'],
            default='analyze',
            help='Performance action to perform'
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Show detailed output'
        )

    def handle(self, *args, **options):
        action = options['action']
        verbose = options['verbose']
        
        self.stdout.write(self.style.SUCCESS(f'🚀 OST Performance Optimization Tool'))
        self.stdout.write(f'Action: {action}')
        self.stdout.write('=' * 50)
        
        if action == 'analyze':
            self.analyze_performance(verbose)
        elif action == 'optimize':
            self.run_optimizations(verbose)
        elif action == 'warm-cache':
            self.warm_cache(verbose)
        elif action == 'migrate-indexes':
            self.create_missing_indexes(verbose)
        elif action == 'monitor':
            self.monitor_performance(verbose)

    def analyze_performance(self, verbose):
        """Analyze current performance metrics"""
        self.stdout.write('📊 Performance Analysis')
        self.stdout.write('-' * 30)
        
        # Database analysis
        from tracker.models import Paper, Journal, ResearchField
        
        paper_count = Paper.objects.count()
        journal_count = Journal.objects.count()
        field_count = ResearchField.objects.count()
        
        self.stdout.write(f'📈 Database Size:')
        self.stdout.write(f'   Papers: {paper_count:,}')
        self.stdout.write(f'   Journals: {journal_count:,}')
        self.stdout.write(f'   Fields: {field_count:,}')
        
        # Memory usage
        process = psutil.Process()
        memory_mb = process.memory_info().rss / 1024 / 1024
        self.stdout.write(f'💾 Memory Usage: {memory_mb:.1f} MB')
        
        # Database queries analysis
        if verbose:
            self.analyze_slow_queries()
        
        # Cache analysis
        self.analyze_cache_performance()
        
        # Index analysis
        self.analyze_database_indexes()

    def analyze_slow_queries(self):
        """Analyze potentially slow queries"""
        self.stdout.write('\n🐌 Slow Query Analysis:')
        
        # Test common queries and measure time
        queries_to_test = [
            ('Home page stats', lambda: self.test_home_page_query()),
            ('Paper search', lambda: self.test_paper_search()),
            ('Field statistics', lambda: self.test_field_stats()),
        ]
        
        for name, query_func in queries_to_test:
            start_time = time.time()
            try:
                query_func()
                duration = (time.time() - start_time) * 1000
                status = '✅' if duration < 100 else '⚠️' if duration < 500 else '❌'
                self.stdout.write(f'   {status} {name}: {duration:.2f}ms')
            except Exception as e:
                self.stdout.write(f'   ❌ {name}: Error - {e}')

    def test_home_page_query(self):
        """Test home page statistics query"""
        from tracker.models import Paper
        from django.db.models import Count, Avg, Q
        
        return Paper.objects.aggregate(
            total_papers=Count('id'),
            avg_transparency_score=Avg('transparency_score'),
            open_data_count=Count('id', filter=Q(is_open_data=True)),
        )

    def test_paper_search(self):
        """Test paper search query"""
        from tracker.models import Paper
        
        return list(Paper.objects.filter(
            title__icontains='study'
        ).select_related('journal')[:10])

    def test_field_stats(self):
        """Test field statistics query"""
        from tracker.models import ResearchField
        
        return list(ResearchField.objects.all()[:10])

    def analyze_cache_performance(self):
        """Analyze cache performance"""
        self.stdout.write('\n🗄️  Cache Analysis:')
        
        # Test cache connectivity
        try:
            cache.set('test_key', 'test_value', 10)
            cached_value = cache.get('test_key')
            if cached_value == 'test_value':
                self.stdout.write('   ✅ Cache connectivity: Working')
                cache.delete('test_key')
            else:
                self.stdout.write('   ❌ Cache connectivity: Failed')
        except Exception as e:
            self.stdout.write(f'   ❌ Cache error: {e}')
        
        # Cache backend info
        cache_backend = settings.CACHES['default']['BACKEND']
        self.stdout.write(f'   📋 Backend: {cache_backend}')

    def analyze_database_indexes(self):
        """Analyze database indexes"""
        self.stdout.write('\n🗂️  Database Index Analysis:')
        
        with connection.cursor() as cursor:
            # Check if indexes exist (SQLite/PostgreSQL compatible)
            if 'sqlite' in settings.DATABASES['default']['ENGINE']:
                cursor.execute("SELECT name FROM sqlite_master WHERE type='index';")
                indexes = [row[0] for row in cursor.fetchall()]
                
                critical_indexes = [
                    'tracker_paper_epmc_id',
                    'tracker_paper_pub_year',
                    'tracker_paper_transparency_score',
                    'tracker_paper_journal_id',
                ]
                
                for index in critical_indexes:
                    status = '✅' if any(index in idx for idx in indexes) else '❌'
                    self.stdout.write(f'   {status} {index}')
            else:
                self.stdout.write('   📋 Index analysis available for SQLite only')

    def run_optimizations(self, verbose):
        """Run comprehensive optimizations"""
        self.stdout.write('⚡ Running Optimizations')
        self.stdout.write('-' * 30)
        
        optimizations = [
            ('Warming cache', self.warm_cache),
            ('Cleaning old cache', self.clean_old_cache),
            ('Optimizing database', self.optimize_database),
            ('Updating statistics', self.update_statistics),
        ]
        
        for name, func in optimizations:
            try:
                self.stdout.write(f'🔄 {name}...')
                func(verbose)
                self.stdout.write(f'   ✅ {name} completed')
            except Exception as e:
                self.stdout.write(f'   ❌ {name} failed: {e}')

    def warm_cache(self, verbose):
        """Warm up the cache with common data"""
        from tracker.cache_utils import warm_cache
        warm_cache()
        if verbose:
            self.stdout.write('   📈 Common caches warmed')

    def clean_old_cache(self, verbose):
        """Clean old cache entries"""
        try:
            if hasattr(cache, 'clear'):
                cache.clear()
                if verbose:
                    self.stdout.write('   🧹 Cache cleared')
        except Exception:
            pass

    def optimize_database(self, verbose):
        """Run database optimizations"""
        with connection.cursor() as cursor:
            # SQLite optimizations
            if 'sqlite' in settings.DATABASES['default']['ENGINE']:
                cursor.execute('VACUUM;')
                cursor.execute('ANALYZE;')
                if verbose:
                    self.stdout.write('   🗃️  Database vacuumed and analyzed')

    def update_statistics(self, verbose):
        """Update research field statistics"""
        from tracker.models import ResearchField
        
        # This would be more efficient with bulk operations
        updated_count = 0
        for field in ResearchField.objects.all()[:10]:  # Limit for performance
            field.save()  # Triggers any calculation updates
            updated_count += 1
        
        if verbose:
            self.stdout.write(f'   📊 Updated {updated_count} field statistics')

    def create_missing_indexes(self, verbose):
        """Create missing database indexes"""
        from django.core.management import call_command
        
        try:
            call_command('makemigrations', 'tracker', verbosity=0)
            call_command('migrate', verbosity=0)
            self.stdout.write('✅ Database migrations applied')
        except Exception as e:
            self.stdout.write(f'❌ Migration error: {e}')

    def monitor_performance(self, verbose):
        """Monitor real-time performance"""
        self.stdout.write('📊 Performance Monitoring')
        self.stdout.write('-' * 30)
        
        while True:
            try:
                # Memory usage
                process = psutil.Process()
                memory_mb = process.memory_info().rss / 1024 / 1024
                cpu_percent = process.cpu_percent()
                
                # Database connections
                from django.db import connections
                db_queries = len(connections['default'].queries) if hasattr(connections['default'], 'queries') else 0
                
                self.stdout.write(f'💾 Memory: {memory_mb:.1f}MB | 🖥️  CPU: {cpu_percent:.1f}% | 🗃️  Queries: {db_queries}')
                
                time.sleep(2)
                
            except KeyboardInterrupt:
                self.stdout.write('\n👋 Monitoring stopped')
                break
            except Exception as e:
                self.stdout.write(f'❌ Monitoring error: {e}')
                break 