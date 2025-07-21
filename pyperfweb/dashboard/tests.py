from django.test import TestCase, Client
from django.urls import reverse
from unittest.mock import patch, MagicMock
import json
from datetime import datetime, timezone
from .models import PerformanceRecord, PerformanceMetrics


class MockDynamoDBService:
    """Mock DynamoDB service for testing without external dependencies."""
    
    @staticmethod
    def create_mock_record(record_id="1753035074369502", session_id="test_session_123", 
                          hostname="test-host", function_name="test_function"):
        """Create a mock PerformanceRecord for testing."""
        return PerformanceRecord(
            id=record_id,
            session_id=session_id,
            timestamp=1642681200.0,  # 2022-01-20 12:00:00 UTC
            hostname=hostname,
            total_calls=100,
            total_wall_time=5.5,
            total_cpu_time=3.2,
            data={
                'function_summaries': {
                    function_name: {
                        'call_count': 50,
                        'wall_time': {
                            'average': 0.1,
                            'total': 5.0,
                            'min': 0.05,
                            'max': 0.5
                        },
                        'cpu_time': {
                            'average': 0.06,
                            'total': 3.0,
                            'min': 0.03,
                            'max': 0.3
                        }
                    },
                    'slow_io_operation': {
                        'call_count': 25,
                        'wall_time': {
                            'average': 0.02,
                            'total': 0.5,
                            'min': 0.01,
                            'max': 0.1
                        },
                        'cpu_time': {
                            'average': 0.008,
                            'total': 0.2,
                            'min': 0.005,
                            'max': 0.05
                        }
                    },
                    'cpu_intensive_task': {
                        'call_count': 25,
                        'wall_time': {
                            'average': 0.015,
                            'total': 0.375,
                            'min': 0.01,
                            'max': 0.03
                        },
                        'cpu_time': {
                            'average': 0.014,
                            'total': 0.35,
                            'min': 0.01,
                            'max': 0.025
                        }
                    }
                },
                'detailed_results': {}
            }
        )
    
    @staticmethod
    def create_mock_metrics():
        """Create mock PerformanceMetrics for testing."""
        return PerformanceMetrics(
            total_records=10,
            total_sessions=3,
            unique_hostnames=['test-host-1', 'test-host-2'],
            unique_functions=['test_function', 'slow_io_operation', 'cpu_intensive_task'],
            date_range=(1642681200.0, 1642767600.0),
            avg_session_duration=300.0,
            slowest_functions_global=[
                ('test_function', 0.1),
                ('slow_io_operation', 0.02),
                ('cpu_intensive_task', 0.015)
            ],
            most_active_hosts=[
                ('test-host-1', 150),
                ('test-host-2', 100)
            ]
        )


class DashboardViewTests(TestCase):
    """Unit tests for dashboard views with mocked dependencies."""
    
    def setUp(self):
        self.client = Client()
        self.mock_record = MockDynamoDBService.create_mock_record()
        self.mock_metrics = MockDynamoDBService.create_mock_metrics()
    
    @patch('pyperfweb.dashboard.views.dynamodb_service')
    def test_dashboard_home_view(self, mock_service):
        """Test dashboard home view."""
        # Setup mocks
        mock_service.get_performance_metrics.return_value = self.mock_metrics
        mock_service.get_recent_records.return_value = [self.mock_record]
        mock_service.get_unique_hostnames.return_value = ['test-host-1', 'test-host-2']
        mock_service.get_unique_function_names.return_value = ['test_function', 'slow_io_operation']
        
        # Make request
        response = self.client.get(reverse('dashboard:home'))
        
        # Assertions
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'test-host-1')
        self.assertContains(response, 'test_function')
        
        # Verify service calls
        mock_service.get_performance_metrics.assert_called_once()
        mock_service.get_recent_records.assert_called_once_with(hours=24, limit=20)
        mock_service.get_unique_hostnames.assert_called_once()
        mock_service.get_unique_function_names.assert_called_once()
    
    @patch('pyperfweb.dashboard.views.dynamodb_service')
    def test_dashboard_home_view_error_handling(self, mock_service):
        """Test dashboard home view error handling."""
        # Setup mock to raise exception
        mock_service.get_performance_metrics.side_effect = Exception("DynamoDB connection error")
        
        # Make request - dashboard_home doesn't have try/catch, so it will raise
        with self.assertRaises(Exception):
            self.client.get(reverse('dashboard:home'))
    
    @patch('pyperfweb.dashboard.views.dynamodb_service')
    def test_performance_records_view(self, mock_service):
        """Test performance records view."""
        # Setup mocks
        mock_service.get_filtered_records.return_value = [self.mock_record]
        mock_service.get_unique_hostnames.return_value = ['test-host-1']
        mock_service.get_unique_function_names.return_value = ['test_function']
        
        # Make request
        response = self.client.get(reverse('dashboard:records'))
        
        # Assertions
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'test-host')
        self.assertContains(response, '100')  # total_calls
        
        # Verify service calls
        mock_service.get_filtered_records.assert_called_once()
        mock_service.get_unique_hostnames.assert_called_once()
        mock_service.get_unique_function_names.assert_called_once()
    
    @patch('pyperfweb.dashboard.views.dynamodb_service')
    def test_performance_records_view_with_filters(self, mock_service):
        """Test performance records view with filters."""
        # Setup mocks
        mock_service.get_filtered_records.return_value = [self.mock_record]
        mock_service.get_unique_hostnames.return_value = ['test-host-1']
        mock_service.get_unique_function_names.return_value = ['test_function']
        
        # Make request with filters
        response = self.client.get(reverse('dashboard:records'), {
            'hostname': 'test-host-1',
            'function_name': 'test_function',
            'sort_by': 'hostname',
            'order': 'asc'
        })
        
        # Assertions
        self.assertEqual(response.status_code, 200)
        
        # Verify service was called with correct parameters
        call_args = mock_service.get_filtered_records.call_args
        self.assertIsNotNone(call_args)
    
    @patch('pyperfweb.dashboard.views.dynamodb_service')
    def test_record_detail_view_valid_record(self, mock_service):
        """Test record detail view with valid record."""
        # Setup mocks
        mock_service.get_all_records.return_value = [self.mock_record]
        mock_service.get_records_by_session.return_value = [self.mock_record]
        
        # Make request
        response = self.client.get(reverse('dashboard:record_detail', args=['1753035074369502']))
        
        # Assertions
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '1753035074369502')
        self.assertContains(response, 'test-host')
        self.assertContains(response, 'test_function')
        
        # Verify service calls
        mock_service.get_all_records.assert_called_once_with(limit=1000)
        mock_service.get_records_by_session.assert_called_once_with('test_session_123')
    
    @patch('pyperfweb.dashboard.views.dynamodb_service')
    def test_record_detail_view_invalid_record(self, mock_service):
        """Test record detail view with invalid record ID."""
        # Setup mocks - return empty list (no matching record)
        mock_service.get_all_records.return_value = []
        
        # Make request
        response = self.client.get(reverse('dashboard:record_detail', args=['invalid_id']))
        
        # Assertions
        self.assertEqual(response.status_code, 404)
        
        # Verify service calls
        mock_service.get_all_records.assert_called_once_with(limit=1000)
    
    @patch('pyperfweb.dashboard.views.dynamodb_service')
    def test_record_detail_view_service_error(self, mock_service):
        """Test record detail view with service error."""
        # Setup mock to raise exception
        mock_service.get_all_records.side_effect = Exception("DynamoDB error")
        
        # Make request
        response = self.client.get(reverse('dashboard:record_detail', args=['1753035074369502']))
        
        # Assertions
        self.assertEqual(response.status_code, 500)
    
    @patch('pyperfweb.dashboard.views.dynamodb_service')
    def test_function_analysis_view_existing_function(self, mock_service):
        """Test function analysis view with existing function."""
        # Setup mocks
        mock_service.get_records_with_function.return_value = [self.mock_record]
        
        # Make request
        response = self.client.get(reverse('dashboard:function_analysis', args=['test_function']))
        
        # Assertions
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'test_function')
        self.assertContains(response, '50')  # call count
        
        # Verify service calls
        mock_service.get_records_with_function.assert_called_once_with('test_function', limit=200)
    
    @patch('pyperfweb.dashboard.views.dynamodb_service')
    def test_function_analysis_view_nonexistent_function(self, mock_service):
        """Test function analysis view with non-existent function."""
        # Setup mocks - return empty list
        mock_service.get_records_with_function.return_value = []
        
        # Make request
        response = self.client.get(reverse('dashboard:function_analysis', args=['nonexistent_function']))
        
        # Assertions
        self.assertEqual(response.status_code, 404)
        
        # Verify service calls
        mock_service.get_records_with_function.assert_called_once_with('nonexistent_function', limit=200)
    
    @patch('pyperfweb.dashboard.views.dynamodb_service')
    def test_function_analysis_view_service_error(self, mock_service):
        """Test function analysis view with service error."""
        # Setup mock to raise exception
        mock_service.get_records_with_function.side_effect = Exception("DynamoDB error")
        
        # Make request
        response = self.client.get(reverse('dashboard:function_analysis', args=['test_function']))
        
        # Assertions
        self.assertEqual(response.status_code, 500)
    
    @patch('pyperfweb.dashboard.views.dynamodb_service')
    def test_api_metrics_view(self, mock_service):
        """Test API metrics endpoint."""
        # Setup mocks
        mock_service.get_performance_metrics.return_value = self.mock_metrics
        
        # Make request
        response = self.client.get(reverse('dashboard:api_metrics'))
        
        # Assertions
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/json')
        
        # Parse JSON response
        data = json.loads(response.content)
        self.assertEqual(data['total_records'], 10)
        self.assertEqual(data['total_sessions'], 3)
        self.assertIn('test-host-1', data['most_active_hosts'][0])
        
        # Verify service calls
        mock_service.get_performance_metrics.assert_called_once()
    
    @patch('pyperfweb.dashboard.views.dynamodb_service')
    def test_api_metrics_view_with_filters(self, mock_service):
        """Test API metrics endpoint with filters."""
        # Setup mocks
        mock_service.get_performance_metrics.return_value = self.mock_metrics
        
        # Make request with query parameters
        response = self.client.get(reverse('dashboard:api_metrics'), {
            'hostname': 'test-host-1',
            'function_name': 'test_function',
            'start_date': '2022-01-20',
            'end_date': '2022-01-21'
        })
        
        # Assertions
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/json')
        
        # Verify service was called with parameters
        call_args = mock_service.get_performance_metrics.call_args
        self.assertIsNotNone(call_args)
    
    @patch('pyperfweb.dashboard.views.dynamodb_service')
    def test_api_hostnames_view(self, mock_service):
        """Test API hostnames endpoint."""
        # Setup mocks
        mock_service.get_unique_hostnames.return_value = ['test-host-1', 'test-host-2']
        
        # Make request
        response = self.client.get(reverse('dashboard:api_hostnames'))
        
        # Assertions
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/json')
        
        # Parse JSON response
        data = json.loads(response.content)
        self.assertEqual(data['hostnames'], ['test-host-1', 'test-host-2'])
        
        # Verify service calls
        mock_service.get_unique_hostnames.assert_called_once()
    
    @patch('pyperfweb.dashboard.views.dynamodb_service')
    def test_api_functions_view(self, mock_service):
        """Test API functions endpoint."""
        # Setup mocks
        mock_service.get_unique_function_names.return_value = ['test_function', 'slow_io_operation']
        
        # Make request
        response = self.client.get(reverse('dashboard:api_functions'))
        
        # Assertions
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/json')
        
        # Parse JSON response
        data = json.loads(response.content)
        self.assertEqual(data['functions'], ['test_function', 'slow_io_operation'])
        
        # Verify service calls
        mock_service.get_unique_function_names.assert_called_once()


class EdgeCaseTests(TestCase):
    """Test edge cases and error scenarios."""
    
    def setUp(self):
        self.client = Client()
    
    @patch('pyperfweb.dashboard.views.dynamodb_service')
    def test_empty_database_scenarios(self, mock_service):
        """Test views when database is empty."""
        # Setup mocks to return empty data
        mock_service.get_performance_metrics.return_value = PerformanceMetrics(
            total_records=0, total_sessions=0, unique_hostnames=[], 
            unique_functions=[], date_range=(None, None), avg_session_duration=0.0,
            slowest_functions_global=[], most_active_hosts=[]
        )
        mock_service.get_recent_records.return_value = []
        mock_service.get_unique_hostnames.return_value = []
        mock_service.get_unique_function_names.return_value = []
        mock_service.get_filtered_records.return_value = []
        
        # Test all main views with empty data
        views_to_test = [
            reverse('dashboard:home'),
            reverse('dashboard:records'),
            reverse('dashboard:api_metrics'),
            reverse('dashboard:api_hostnames'),
            reverse('dashboard:api_functions'),
        ]
        
        for url in views_to_test:
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200, f"Failed for URL: {url}")
    
    def test_invalid_urls(self):
        """Test invalid URL patterns."""
        # Test URLs that should return 404
        invalid_urls = [
            '/invalid_path/',
            '/functions/',  # Missing function name
        ]
        
        for url in invalid_urls:
            response = self.client.get(url)
            # Should return 404 or redirect, not 500
            self.assertIn(response.status_code, [404, 301, 302], f"Unexpected status for {url}")
    
    @patch('pyperfweb.dashboard.views.dynamodb_service')
    def test_malformed_date_filters(self, mock_service):
        """Test performance records view with malformed date filters."""
        # Setup basic mocks
        mock_service.get_filtered_records.return_value = []
        mock_service.get_unique_hostnames.return_value = []
        mock_service.get_unique_function_names.return_value = []
        
        # Test with invalid date formats
        response = self.client.get(reverse('dashboard:records'), {
            'start_date': 'invalid-date',
            'end_date': 'also-invalid',
        })
        
        # Should handle gracefully
        self.assertEqual(response.status_code, 200)
    
    @patch('pyperfweb.dashboard.views.dynamodb_service')
    def test_special_characters_in_function_names(self, mock_service):
        """Test function analysis with special characters in function names."""
        # Setup mocks
        mock_service.get_records_with_function.return_value = []
        
        # Test function names with special characters
        special_names = [
            'function.with.dots',
            'function_with_underscores',
            'function-with-dashes',
            'function123',
        ]
        
        for name in special_names:
            response = self.client.get(reverse('dashboard:function_analysis', args=[name]))
            # Should handle gracefully, either 200 (empty results) or 404
            self.assertIn(response.status_code, [200, 404], f"Failed for function name: {name}")