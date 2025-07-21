#!/usr/bin/env python3
"""
Automated test script for PyPerf Django web dashboard.
Starts server, runs tests, and reports results.
"""

import os
import sys
import time
import signal
import subprocess
import requests
import json
from datetime import datetime
from threading import Thread


class DjangoTester:
    def __init__(self):
        self.server_process = None
        self.base_url = "http://127.0.0.1:8000"
        self.test_results = []
        
    def kill_existing_server(self):
        """Kill any existing Django server on port 8000."""
        try:
            result = subprocess.run(['lsof', '-ti:8000'], capture_output=True, text=True)
            if result.stdout.strip():
                pids = result.stdout.strip().split('\n')
                for pid in pids:
                    try:
                        os.kill(int(pid), signal.SIGKILL)
                        print(f"✓ Killed existing process {pid}")
                    except (ProcessLookupError, ValueError):
                        pass
        except Exception as e:
            print(f"Note: {e}")
    
    def start_server(self):
        """Start Django development server."""
        print("🚀 Starting Django server...")
        
        # Kill any existing server first
        self.kill_existing_server()
        time.sleep(1)
        
        # Activate virtual environment and start server
        cmd = [
            'bash', '-c', 
            'source venv/bin/activate && python manage.py runserver 8000 --noreload'
        ]
        
        self.server_process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            preexec_fn=os.setsid
        )
        
        # Wait for server to start and capture startup output
        for i in range(30):  # Wait up to 30 seconds
            try:
                response = requests.get(f"{self.base_url}/", timeout=1)
                if response.status_code in [200, 404, 500]:  # Server is responding
                    print(f"✓ Server started successfully (attempt {i+1})")
                    
                    # Display server startup output (including config info)
                    if i == 0:  # Only show on first successful attempt
                        time.sleep(0.5)  # Give server time to output config
                        try:
                            # Read any available stdout/stderr
                            stdout_data = self.server_process.stdout.read(8192).decode('utf-8', errors='ignore')
                            stderr_data = self.server_process.stderr.read(8192).decode('utf-8', errors='ignore')
                            
                            if stdout_data and ('PYPERFWEB SERVER CONFIGURATION' in stdout_data or 'config' in stdout_data.lower()):
                                print("\n📋 Server startup output:")
                                print(stdout_data.strip())
                            if stderr_data and ('PYPERFWEB SERVER CONFIGURATION' in stderr_data or 'config' in stderr_data.lower()):
                                print("\n📋 Server configuration info:")
                                print(stderr_data.strip())
                                
                        except Exception as e:
                            print(f"Note: Could not capture server output: {e}")
                    
                    return True
            except requests.exceptions.RequestException:
                time.sleep(1)
        
        print("✗ Failed to start server")
        return False
    
    def stop_server(self):
        """Stop Django development server."""
        if self.server_process:
            try:
                os.killpg(os.getpgid(self.server_process.pid), signal.SIGTERM)
                self.server_process.wait(timeout=5)
                print("✓ Server stopped")
            except Exception as e:
                print(f"Note: {e}")
    
    def test_endpoint(self, endpoint, expected_status=200, method='GET', description=""):
        """Test a single endpoint."""
        url = f"{self.base_url}{endpoint}"
        test_name = description or f"{method} {endpoint}"
        
        try:
            if method == 'GET':
                response = requests.get(url, timeout=10)
            else:
                response = requests.request(method, url, timeout=10)
            
            success = response.status_code == expected_status
            result = {
                'test': test_name,
                'url': url,
                'expected': expected_status,
                'actual': response.status_code,
                'success': success,
                'response_time': response.elapsed.total_seconds(),
                'content_length': len(response.content)
            }
            
            status_icon = "✓" if success else "✗"
            print(f"{status_icon} {test_name}: {response.status_code} ({response.elapsed.total_seconds():.3f}s)")
            
            self.test_results.append(result)
            return result
            
        except Exception as e:
            result = {
                'test': test_name,
                'url': url,
                'expected': expected_status,
                'actual': 'ERROR',
                'success': False,
                'error': str(e),
                'response_time': 0,
                'content_length': 0
            }
            print(f"✗ {test_name}: ERROR - {e}")
            self.test_results.append(result)
            return result
    
    def run_url_tests(self):
        """Test all main URL endpoints."""
        print("\n📋 Testing main URL endpoints...")
        
        # Main dashboard
        self.test_endpoint("/", description="Dashboard Home")
        
        # Performance records
        self.test_endpoint("/records/", description="Performance Records List")
        
        # Records with filters
        self.test_endpoint("/records/?hostname=test", description="Records with hostname filter")
        self.test_endpoint("/records/?start_date=2025-01-01", description="Records with date filter")
        
        # API endpoints
        self.test_endpoint("/api/metrics/", description="API Metrics")
        self.test_endpoint("/api/hostnames/", description="API Hostnames")
        self.test_endpoint("/api/functions/", description="API Functions")
        
    
    def run_api_tests(self):
        """Test API endpoints for proper JSON responses."""
        print("\n🔌 Testing API endpoints...")
        
        api_endpoints = [
            "/api/metrics/",
            "/api/hostnames/",
            "/api/functions/"
        ]
        
        for endpoint in api_endpoints:
            result = self.test_endpoint(endpoint, description=f"API {endpoint}")
            
            if result['success']:
                # Test if response is valid JSON
                try:
                    url = f"{self.base_url}{endpoint}"
                    response = requests.get(url)
                    json.loads(response.text)
                    print(f"  ✓ Valid JSON response")
                except json.JSONDecodeError:
                    print(f"  ✗ Invalid JSON response")
                    result['success'] = False
    
    def run_function_analysis_tests(self):
        """Test function analysis view with various scenarios."""
        print("\n🔍 Testing function analysis...")
        
        # Test with non-existent function (should return 404)
        self.test_endpoint("/functions/nonexistent_function/", 
                         expected_status=404,  # Should return 404 for non-existent function
                         description="Function analysis - non-existent function")
        
        # Test with common function names that might exist in sample data
        common_functions = [
            "cpu_intensive_task",
            "slow_io_operation", 
            "mixed_workload",
            "fast_calculation",
            "variable_duration"
        ]
        
        for func_name in common_functions:
            self.test_endpoint(f"/functions/{func_name}/",
                             expected_status=200,
                             description=f"Function analysis - {func_name}")
        
        # Test function names with special characters (URL encoding)
        special_function_names = [
            "function_with_underscores",
            "function-with-dashes",  # Should be URL safe
            "function123",  # With numbers
        ]
        
        for func_name in special_function_names:
            self.test_endpoint(f"/functions/{func_name}/",
                             expected_status=404,  # These functions likely don't exist in sample data
                             description=f"Function analysis - {func_name} (special chars)")
        
        # Test very long function name (edge case)
        long_function_name = "very_long_function_name_that_might_cause_issues_with_url_handling"
        self.test_endpoint(f"/functions/{long_function_name}/",
                         expected_status=404,  # This function likely doesn't exist
                         description="Function analysis - long function name")

    def run_error_handling_tests(self):
        """Test error handling."""
        print("\n🚨 Testing error handling...")
        
        # Test 404 endpoints
        self.test_endpoint("/nonexistent/", expected_status=404, description="404 Not Found")
        
        # Test record detail with invalid ID (should return 404)
        self.test_endpoint("/records/invalid_id/", 
                         expected_status=404,  # Should return 404 for invalid record ID
                         description="Invalid record ID")
    
    def run_performance_tests(self):
        """Basic performance tests."""
        print("\n⚡ Testing performance...")
        
        endpoints = ["/", "/records/", "/api/metrics/"]
        
        for endpoint in endpoints:
            result = self.test_endpoint(endpoint, description=f"Performance {endpoint}")
            
            if result['success']:
                response_time = result['response_time']
                if response_time > 5.0:
                    print(f"  ⚠ Slow response: {response_time:.3f}s")
                elif response_time > 2.0:
                    print(f"  ⚠ Moderate response time: {response_time:.3f}s")
                else:
                    print(f"  ✓ Fast response: {response_time:.3f}s")
    
    def print_summary(self):
        """Print test summary."""
        print("\n" + "="*60)
        print("📊 TEST SUMMARY")
        print("="*60)
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for r in self.test_results if r['success'])
        failed_tests = total_tests - passed_tests
        
        print(f"Total Tests: {total_tests}")
        print(f"Passed: {passed_tests} ✓")
        print(f"Failed: {failed_tests} ✗")
        print(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")
        
        if failed_tests > 0:
            print(f"\n❌ FAILED TESTS:")
            for result in self.test_results:
                if not result['success']:
                    print(f"  • {result['test']}: {result.get('actual', 'ERROR')}")
                    if 'error' in result:
                        print(f"    Error: {result['error']}")
        
        # Performance summary
        response_times = [r['response_time'] for r in self.test_results if r['success']]
        if response_times:
            avg_time = sum(response_times) / len(response_times)
            max_time = max(response_times)
            print(f"\n⚡ PERFORMANCE:")
            print(f"  Average response time: {avg_time:.3f}s")
            print(f"  Slowest response time: {max_time:.3f}s")
        
        return failed_tests == 0
    
    def run_all_tests(self):
        """Run complete test suite."""
        print("🧪 PyPerf Django Server Test Suite")
        print("=" * 60)
        print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        try:
            # Start server
            if not self.start_server():
                print("❌ Cannot start server - aborting tests")
                return False
            
            # Wait a moment for server to fully initialize
            time.sleep(2)
            
            # Run test suites
            self.run_url_tests()
            self.run_api_tests()
            self.run_function_analysis_tests()
            self.run_error_handling_tests()
            self.run_performance_tests()
            
            # Print summary
            success = self.print_summary()
            
            return success
            
        except KeyboardInterrupt:
            print("\n⏹ Tests interrupted by user")
            return False
        except Exception as e:
            print(f"\n❌ Test suite error: {e}")
            return False
        finally:
            self.stop_server()


def main():
    """Main function."""
    tester = DjangoTester()
    success = tester.run_all_tests()
    
    exit_code = 0 if success else 1
    
    print(f"\n🏁 Test suite completed with exit code: {exit_code}")
    sys.exit(exit_code)


if __name__ == "__main__":
    main()