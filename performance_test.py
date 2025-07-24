#!/usr/bin/env python3
"""
Performance Testing Script for Open Science Tracker

This script tests various aspects of the web application performance
including page load times, database query efficiency, API response times,
and memory usage.
"""

import time
import requests
import statistics
import psutil
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
import matplotlib.pyplot as plt
import seaborn as sns


class PerformanceTester:
    """Comprehensive performance testing for OST"""
    
    def __init__(self, base_url="https://ost.xeradb.com"):
        self.base_url = base_url
        self.results = {}
        self.session = requests.Session()
        
        # Configure session for performance
        self.session.headers.update({
            'User-Agent': 'OST-Performance-Tester/1.0',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive'
        })
    
    def run_comprehensive_test(self):
        """Run all performance tests"""
        print("🚀 Starting Comprehensive Performance Test")
        print("=" * 50)
        
        test_suite = [
            ("Page Load Performance", self.test_page_performance),
            ("API Response Times", self.test_api_performance),
            ("Database Query Efficiency", self.test_database_performance),
            ("Concurrent Load Testing", self.test_concurrent_load),
            ("Memory Usage Analysis", self.test_memory_usage),
            ("Cache Effectiveness", self.test_cache_performance),
            ("Search Performance", self.test_search_performance),
        ]
        
        for test_name, test_func in test_suite:
            print(f"\n📊 Running: {test_name}")
            try:
                result = test_func()
                self.results[test_name] = result
                self.print_test_results(test_name, result)
            except Exception as e:
                print(f"❌ Test failed: {e}")
                self.results[test_name] = {"error": str(e)}
        
        self.generate_performance_report()
    
    def test_page_performance(self):
        """Test page load performance for key pages"""
        pages = [
            ("/", "Home Page"),
            ("/papers/", "Papers List"),
            ("/journals/", "Journals List"),
            ("/statistics/", "Statistics Page"),
            ("/papers/?search=covid&page_size=50", "Search Results"),
            ("/api/", "API Overview"),
        ]
        
        results = {}
        
        for url, name in pages:
            print(f"  Testing {name}...")
            times = []
            
            for i in range(10):  # 10 tests per page
                start_time = time.time()
                try:
                    response = self.session.get(f"{self.base_url}{url}", timeout=30)
                    end_time = time.time()
                    
                    if response.status_code == 200:
                        load_time = end_time - start_time
                        times.append(load_time)
                        
                        # Check for performance headers
                        response_time_header = response.headers.get('X-Response-Time')
                        query_count_header = response.headers.get('X-DB-Query-Count')
                        cache_status = response.headers.get('X-Cache-Status')
                        
                    else:
                        print(f"    ⚠️ HTTP {response.status_code} for {name}")
                        
                except requests.exceptions.RequestException as e:
                    print(f"    ❌ Request failed for {name}: {e}")
                    continue
            
            if times:
                results[name] = {
                    'avg_time': statistics.mean(times),
                    'min_time': min(times),
                    'max_time': max(times),
                    'median_time': statistics.median(times),
                    'std_dev': statistics.stdev(times) if len(times) > 1 else 0,
                    'success_rate': len(times) / 10 * 100,
                    'response_time_header': response_time_header,
                    'query_count': query_count_header,
                    'cache_status': cache_status
                }
        
        return results
    
    def test_api_performance(self):
        """Test API endpoint performance"""
        api_endpoints = [
            ("/api/", "API Overview"),
            ("/api/v1/papers/?page_size=50", "Papers List API"),
            ("/api/v1/papers/transparency_stats/", "Transparency Stats"),
            ("/api/v1/journals/?page_size=50", "Journals List API"),
            ("/api/v1/papers/?transparency_score__gte=5", "High Transparency Papers"),
            ("/api/v1/papers/?pub_year=2023", "2023 Papers"),
            ("/api/v1/papers/by_year/", "Papers by Year"),
        ]
        
        results = {}
        
        for endpoint, name in api_endpoints:
            print(f"  Testing {name}...")
            times = []
            response_sizes = []
            
            for i in range(5):  # 5 tests per API endpoint
                start_time = time.time()
                try:
                    response = self.session.get(f"{self.base_url}{endpoint}", timeout=30)
                    end_time = time.time()
                    
                    if response.status_code == 200:
                        load_time = end_time - start_time
                        times.append(load_time)
                        response_sizes.append(len(response.content))
                        
                        # Parse JSON to check data quality
                        try:
                            data = response.json()
                            if isinstance(data, dict) and 'results' in data:
                                result_count = len(data['results'])
                            elif isinstance(data, dict) and 'total_papers' in data:
                                result_count = data['total_papers']
                            else:
                                result_count = len(data) if isinstance(data, list) else 1
                        except:
                            result_count = 0
                    else:
                        print(f"    ⚠️ HTTP {response.status_code} for {name}")
                        
                except requests.exceptions.RequestException as e:
                    print(f"    ❌ Request failed for {name}: {e}")
                    continue
            
            if times:
                results[name] = {
                    'avg_time': statistics.mean(times),
                    'min_time': min(times),
                    'max_time': max(times),
                    'avg_response_size': statistics.mean(response_sizes),
                    'result_count': result_count,
                    'throughput': result_count / statistics.mean(times) if times else 0
                }
        
        return results
    
    def test_database_performance(self):
        """Test database query efficiency through API endpoints"""
        print("  Testing database query patterns...")
        
        # Test queries that might have N+1 problems
        test_queries = [
            ("/api/v1/papers/?page_size=100", "Large Paper List"),
            ("/api/v1/journals/?min_papers=10&page_size=50", "Journals with Papers"),
            ("/api/v1/papers/?journal_name=nature", "Papers by Journal"),
            ("/api/v1/papers/?transparency_score__gte=4", "Complex Filter Query"),
        ]
        
        results = {}
        
        for query, name in test_queries:
            print(f"    Testing {name}...")
            start_time = time.time()
            
            try:
                response = self.session.get(f"{self.base_url}{query}")
                end_time = time.time()
                
                query_time = end_time - start_time
                query_count = response.headers.get('X-DB-Query-Count', 'Unknown')
                response_time = response.headers.get('X-Response-Time', 'Unknown')
                
                if response.status_code == 200:
                    data = response.json()
                    if 'results' in data:
                        item_count = len(data['results'])
                        total_count = data.get('count', item_count)
                    else:
                        item_count = 1
                        total_count = 1
                    
                    results[name] = {
                        'query_time': query_time,
                        'db_query_count': query_count,
                        'server_response_time': response_time,
                        'items_returned': item_count,
                        'total_available': total_count,
                        'efficiency_score': item_count / float(query_count) if query_count != 'Unknown' else 0
                    }
                    
            except Exception as e:
                print(f"    ❌ Database test failed for {name}: {e}")
        
        return results
    
    def test_concurrent_load(self):
        """Test performance under concurrent load"""
        print("  Testing concurrent load capacity...")
        
        def make_request(url):
            start_time = time.time()
            try:
                response = self.session.get(url, timeout=30)
                end_time = time.time()
                return {
                    'success': response.status_code == 200,
                    'time': end_time - start_time,
                    'status_code': response.status_code
                }
            except Exception as e:
                return {
                    'success': False,
                    'time': 30,  # timeout
                    'error': str(e)
                }
        
        # Test with different concurrency levels
        concurrency_levels = [1, 5, 10, 20]
        url = f"{self.base_url}/api/v1/papers/?page_size=20"
        
        results = {}
        
        for concurrency in concurrency_levels:
            print(f"    Testing with {concurrency} concurrent requests...")
            
            with ThreadPoolExecutor(max_workers=concurrency) as executor:
                futures = [executor.submit(make_request, url) for _ in range(concurrency)]
                responses = [future.result() for future in as_completed(futures)]
            
            successful_responses = [r for r in responses if r['success']]
            failed_responses = [r for r in responses if not r['success']]
            
            if successful_responses:
                times = [r['time'] for r in successful_responses]
                results[f"{concurrency}_concurrent"] = {
                    'success_rate': len(successful_responses) / len(responses) * 100,
                    'avg_response_time': statistics.mean(times),
                    'max_response_time': max(times),
                    'failed_requests': len(failed_responses),
                    'total_requests': len(responses)
                }
        
        return results
    
    def test_memory_usage(self):
        """Monitor memory usage during operations"""
        print("  Analyzing memory usage patterns...")
        
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Simulate heavy operations
        heavy_operations = [
            f"{self.base_url}/api/v1/papers/?page_size=100",
            f"{self.base_url}/api/v1/papers/transparency_stats/",
            f"{self.base_url}/statistics/",
            f"{self.base_url}/api/v1/journals/?min_papers=50"
        ]
        
        memory_usage = []
        
        for operation in heavy_operations:
            try:
                response = self.session.get(operation)
                current_memory = process.memory_info().rss / 1024 / 1024
                memory_usage.append(current_memory)
                time.sleep(1)  # Allow for garbage collection
            except:
                continue
        
        final_memory = process.memory_info().rss / 1024 / 1024
        
        return {
            'initial_memory_mb': initial_memory,
            'final_memory_mb': final_memory,
            'peak_memory_mb': max(memory_usage) if memory_usage else initial_memory,
            'memory_increase_mb': final_memory - initial_memory,
            'memory_efficiency': 'Good' if final_memory - initial_memory < 50 else 'Needs optimization'
        }
    
    def test_cache_performance(self):
        """Test caching effectiveness"""
        print("  Testing cache performance...")
        
        # Test same endpoint multiple times to check caching
        cache_test_url = f"{self.base_url}/api/v1/papers/transparency_stats/"
        
        # First request (cache miss)
        start_time = time.time()
        response1 = self.session.get(cache_test_url)
        first_request_time = time.time() - start_time
        cache_status_1 = response1.headers.get('X-Cache-Status', 'Unknown')
        
        # Second request (should be cache hit)
        start_time = time.time()
        response2 = self.session.get(cache_test_url)
        second_request_time = time.time() - start_time
        cache_status_2 = response2.headers.get('X-Cache-Status', 'Unknown')
        
        # Third request
        start_time = time.time()
        response3 = self.session.get(cache_test_url)
        third_request_time = time.time() - start_time
        cache_status_3 = response3.headers.get('X-Cache-Status', 'Unknown')
        
        return {
            'first_request_time': first_request_time,
            'second_request_time': second_request_time,
            'third_request_time': third_request_time,
            'cache_status_1': cache_status_1,
            'cache_status_2': cache_status_2,
            'cache_status_3': cache_status_3,
            'cache_effectiveness': second_request_time < first_request_time * 0.5,
            'speed_improvement': f"{((first_request_time - second_request_time) / first_request_time * 100):.1f}%"
        }
    
    def test_search_performance(self):
        """Test search functionality performance"""
        print("  Testing search performance...")
        
        search_terms = [
            "covid",
            "cancer",
            "diabetes",
            "machine learning",
            "clinical trial"
        ]
        
        results = {}
        
        for term in search_terms:
            print(f"    Testing search for '{term}'...")
            search_url = f"{self.base_url}/api/v1/papers/?search={term}&page_size=50"
            
            start_time = time.time()
            try:
                response = self.session.get(search_url)
                end_time = time.time()
                
                if response.status_code == 200:
                    data = response.json()
                    search_time = end_time - start_time
                    result_count = len(data.get('results', []))
                    total_matches = data.get('count', 0)
                    
                    results[term] = {
                        'search_time': search_time,
                        'results_returned': result_count,
                        'total_matches': total_matches,
                        'search_efficiency': total_matches / search_time if search_time > 0 else 0
                    }
            except Exception as e:
                results[term] = {'error': str(e)}
        
        return results
    
    def print_test_results(self, test_name, results):
        """Print formatted test results"""
        print(f"  ✅ {test_name} Results:")
        
        if isinstance(results, dict) and 'error' in results:
            print(f"    ❌ Error: {results['error']}")
            return
        
        for key, value in results.items():
            if isinstance(value, dict):
                print(f"    📋 {key}:")
                for sub_key, sub_value in value.items():
                    if isinstance(sub_value, float):
                        print(f"      {sub_key}: {sub_value:.3f}")
                    else:
                        print(f"      {sub_key}: {sub_value}")
            else:
                if isinstance(value, float):
                    print(f"    {key}: {value:.3f}")
                else:
                    print(f"    {key}: {value}")
    
    def generate_performance_report(self):
        """Generate comprehensive performance report"""
        print("\n" + "=" * 60)
        print("📊 COMPREHENSIVE PERFORMANCE REPORT")
        print("=" * 60)
        
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"Report Generated: {timestamp}")
        print(f"Base URL: {self.base_url}")
        
        # Overall performance summary
        self.print_performance_summary()
        
        # Save detailed results to JSON
        self.save_results_to_file()
        
        # Generate performance charts
        self.generate_performance_charts()
    
    def print_performance_summary(self):
        """Print performance summary with recommendations"""
        print("\n🎯 PERFORMANCE SUMMARY:")
        print("-" * 40)
        
        # Page performance summary
        if "Page Load Performance" in self.results:
            page_results = self.results["Page Load Performance"]
            avg_times = []
            for page, data in page_results.items():
                if isinstance(data, dict) and 'avg_time' in data:
                    avg_times.append(data['avg_time'])
            
            if avg_times:
                overall_avg = statistics.mean(avg_times)
                print(f"📄 Average Page Load Time: {overall_avg:.2f}s")
                
                if overall_avg < 2.0:
                    print("   ✅ Excellent performance!")
                elif overall_avg < 3.0:
                    print("   ⚡ Good performance")
                elif overall_avg < 5.0:
                    print("   ⚠️ Acceptable performance")
                else:
                    print("   ❌ Needs optimization")
        
        # API performance summary
        if "API Response Times" in self.results:
            api_results = self.results["API Response Times"]
            api_times = []
            for endpoint, data in api_results.items():
                if isinstance(data, dict) and 'avg_time' in data:
                    api_times.append(data['avg_time'])
            
            if api_times:
                api_avg = statistics.mean(api_times)
                print(f"🔗 Average API Response Time: {api_avg:.2f}s")
        
        # Database efficiency
        if "Database Query Efficiency" in self.results:
            db_results = self.results["Database Query Efficiency"]
            print(f"🗄️ Database Queries: See detailed results above")
        
        # Cache effectiveness
        if "Cache Effectiveness" in self.results:
            cache_results = self.results["Cache Effectiveness"]
            if cache_results.get('cache_effectiveness'):
                print(f"💾 Cache Performance: ✅ Effective")
            else:
                print(f"💾 Cache Performance: ❌ Needs improvement")
        
        print("\n💡 RECOMMENDATIONS:")
        print("-" * 40)
        
        # Generate recommendations based on results
        recommendations = self.generate_recommendations()
        for rec in recommendations:
            print(f"• {rec}")
    
    def generate_recommendations(self):
        """Generate performance recommendations based on test results"""
        recommendations = []
        
        # Page load recommendations
        if "Page Load Performance" in self.results:
            page_results = self.results["Page Load Performance"]
            slow_pages = []
            for page, data in page_results.items():
                if isinstance(data, dict) and data.get('avg_time', 0) > 3.0:
                    slow_pages.append(page)
            
            if slow_pages:
                recommendations.append(f"Optimize slow pages: {', '.join(slow_pages)}")
        
        # Database recommendations
        if "Database Query Efficiency" in self.results:
            db_results = self.results["Database Query Efficiency"]
            for query, data in db_results.items():
                if isinstance(data, dict):
                    query_count = data.get('db_query_count', 'Unknown')
                    if query_count != 'Unknown' and int(query_count) > 20:
                        recommendations.append(f"Reduce database queries for: {query}")
        
        # Memory recommendations
        if "Memory Usage Analysis" in self.results:
            memory_results = self.results["Memory Usage Analysis"]
            if memory_results.get('memory_increase_mb', 0) > 100:
                recommendations.append("Investigate memory leaks or optimize memory usage")
        
        # Cache recommendations
        if "Cache Effectiveness" in self.results:
            cache_results = self.results["Cache Effectiveness"]
            if not cache_results.get('cache_effectiveness'):
                recommendations.append("Implement or improve caching strategy")
        
        if not recommendations:
            recommendations.append("Performance looks good! Continue monitoring.")
        
        return recommendations
    
    def save_results_to_file(self):
        """Save detailed results to JSON file"""
        filename = f"performance_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        with open(filename, 'w') as f:
            json.dump({
                'timestamp': datetime.now().isoformat(),
                'base_url': self.base_url,
                'results': self.results
            }, f, indent=2, default=str)
        
        print(f"\n💾 Detailed results saved to: {filename}")
    
    def generate_performance_charts(self):
        """Generate performance visualization charts"""
        try:
            import matplotlib.pyplot as plt
            import seaborn as sns
            
            # Set style
            plt.style.use('seaborn-v0_8')
            fig, axes = plt.subplots(2, 2, figsize=(15, 10))
            fig.suptitle('Open Science Tracker Performance Analysis', fontsize=16)
            
            # Page load times chart
            if "Page Load Performance" in self.results:
                page_data = self.results["Page Load Performance"]
                pages = []
                times = []
                for page, data in page_data.items():
                    if isinstance(data, dict) and 'avg_time' in data:
                        pages.append(page.replace(' ', '\n'))
                        times.append(data['avg_time'])
                
                if pages and times:
                    axes[0, 0].bar(pages, times, color='skyblue')
                    axes[0, 0].set_title('Page Load Times')
                    axes[0, 0].set_ylabel('Time (seconds)')
                    axes[0, 0].tick_params(axis='x', rotation=45)
            
            # API response times chart
            if "API Response Times" in self.results:
                api_data = self.results["API Response Times"]
                endpoints = []
                api_times = []
                for endpoint, data in api_data.items():
                    if isinstance(data, dict) and 'avg_time' in data:
                        endpoints.append(endpoint.replace(' ', '\n'))
                        api_times.append(data['avg_time'])
                
                if endpoints and api_times:
                    axes[0, 1].bar(endpoints, api_times, color='lightgreen')
                    axes[0, 1].set_title('API Response Times')
                    axes[0, 1].set_ylabel('Time (seconds)')
                    axes[0, 1].tick_params(axis='x', rotation=45)
            
            # Concurrent load performance
            if "Concurrent Load Testing" in self.results:
                load_data = self.results["Concurrent Load Testing"]
                concurrency = []
                success_rates = []
                for test, data in load_data.items():
                    if isinstance(data, dict) and 'success_rate' in data:
                        concurrency.append(test.replace('_concurrent', ''))
                        success_rates.append(data['success_rate'])
                
                if concurrency and success_rates:
                    axes[1, 0].plot(concurrency, success_rates, marker='o', color='orange')
                    axes[1, 0].set_title('Concurrent Load Performance')
                    axes[1, 0].set_xlabel('Concurrent Requests')
                    axes[1, 0].set_ylabel('Success Rate (%)')
                    axes[1, 0].set_ylim(0, 105)
            
            # Search performance
            if "Search Performance" in self.results:
                search_data = self.results["Search Performance"]
                terms = []
                search_times = []
                for term, data in search_data.items():
                    if isinstance(data, dict) and 'search_time' in data:
                        terms.append(term)
                        search_times.append(data['search_time'])
                
                if terms and search_times:
                    axes[1, 1].bar(terms, search_times, color='lightcoral')
                    axes[1, 1].set_title('Search Performance')
                    axes[1, 1].set_ylabel('Time (seconds)')
                    axes[1, 1].tick_params(axis='x', rotation=45)
            
            plt.tight_layout()
            chart_filename = f"performance_charts_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            plt.savefig(chart_filename, dpi=300, bbox_inches='tight')
            print(f"📊 Performance charts saved to: {chart_filename}")
            
        except ImportError:
            print("📊 Install matplotlib and seaborn to generate performance charts")
        except Exception as e:
            print(f"📊 Could not generate charts: {e}")


def main():
    """Main function to run performance tests"""
    import argparse
    
    parser = argparse.ArgumentParser(description="OST Performance Testing")
    parser.add_argument("--url", default="https://ost.xeradb.com", 
                       help="Base URL to test (default: https://ost.xeradb.com)")
    parser.add_argument("--quick", action="store_true", 
                       help="Run quick test suite")
    
    args = parser.parse_args()
    
    tester = PerformanceTester(args.url)
    
    if args.quick:
        # Quick test - just basic page loads
        print("🏃 Running Quick Performance Test")
        result = tester.test_page_performance()
        tester.print_test_results("Page Load Performance", result)
    else:
        # Full comprehensive test
        tester.run_comprehensive_test()


if __name__ == "__main__":
    main() 