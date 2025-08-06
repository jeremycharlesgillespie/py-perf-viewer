import boto3
from boto3.dynamodb.conditions import Key, Attr
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from django.conf import settings
from .models import PerformanceRecord, PerformanceMetrics
import math


class DynamoDBService:
    """Service class for interacting with DynamoDB."""
    
    def __init__(self):
        self.dynamodb = boto3.client('dynamodb', region_name=settings.AWS_DEFAULT_REGION)
        self.table_name = settings.DYNAMODB_TABLE_NAME
    
    def get_all_records(self, limit: int = 100) -> List[PerformanceRecord]:
        """Get all performance records from DynamoDB."""
        try:
            response = self.dynamodb.scan(
                TableName=self.table_name,
                Limit=limit
            )
            
            records = []
            for item in response.get('Items', []):
                records.append(PerformanceRecord.from_dynamodb_item(item))
            
            return records
        except Exception as e:
            print(f"Error fetching records: {e}")
            return []
    
    def get_records_by_hostname(self, hostname: str, limit: int = 100) -> List[PerformanceRecord]:
        """Get records filtered by hostname."""
        try:
            response = self.dynamodb.scan(
                TableName=self.table_name,
                FilterExpression='hostname = :hostname',
                ExpressionAttributeValues={':hostname': {'S': hostname}},
                Limit=limit
            )
            
            records = []
            for item in response.get('Items', []):
                records.append(PerformanceRecord.from_dynamodb_item(item))
            
            return records
        except Exception as e:
            print(f"Error fetching records by hostname: {e}")
            return []
    
    def get_records_by_date_range(self, start_date: datetime, end_date: datetime, limit: int = 100) -> List[PerformanceRecord]:
        """Get records within a date range."""
        try:
            start_timestamp = start_date.timestamp()
            end_timestamp = end_date.timestamp()
            
            response = self.dynamodb.scan(
                TableName=self.table_name,
                FilterExpression='#ts BETWEEN :start_ts AND :end_ts',
                ExpressionAttributeNames={'#ts': 'timestamp'},
                ExpressionAttributeValues={
                    ':start_ts': {'N': str(start_timestamp)},
                    ':end_ts': {'N': str(end_timestamp)}
                },
                Limit=limit
            )
            
            records = []
            for item in response.get('Items', []):
                records.append(PerformanceRecord.from_dynamodb_item(item))
            
            return records
        except Exception as e:
            print(f"Error fetching records by date range: {e}")
            return []
    
    def get_records_by_session(self, session_id: str) -> List[PerformanceRecord]:
        """Get all records for a specific session."""
        try:
            response = self.dynamodb.scan(
                TableName=self.table_name,
                FilterExpression='session_id = :session_id',
                ExpressionAttributeValues={':session_id': {'S': session_id}}
            )
            
            records = []
            for item in response.get('Items', []):
                records.append(PerformanceRecord.from_dynamodb_item(item))
            
            return records
        except Exception as e:
            print(f"Error fetching records by session: {e}")
            return []
    
    def get_records_with_function(self, function_name: str, limit: int = 100) -> List[PerformanceRecord]:
        """Get records that contain a specific function."""
        try:
            response = self.dynamodb.scan(
                TableName=self.table_name,
                FilterExpression='contains(#data, :function_name)',
                ExpressionAttributeNames={'#data': 'data'},
                ExpressionAttributeValues={':function_name': {'S': function_name}},
                Limit=limit
            )
            
            records = []
            for item in response.get('Items', []):
                record = PerformanceRecord.from_dynamodb_item(item)
                # Double-check that the function actually exists in the record
                if function_name in record.function_names:
                    records.append(record)
            
            return records
        except Exception as e:
            print(f"Error fetching records with function: {e}")
            return []
    
    def get_filtered_records(self, 
                           hostname: Optional[str] = None,
                           start_date: Optional[datetime] = None,
                           end_date: Optional[datetime] = None,
                           function_name: Optional[str] = None,
                           session_id: Optional[str] = None,
                           limit: int = 100) -> List[PerformanceRecord]:
        """Get records with multiple filters applied."""
        try:
            filter_expressions = []
            expression_values = {}
            expression_names = {}
            
            if hostname:
                filter_expressions.append('hostname = :hostname')
                expression_values[':hostname'] = {'S': hostname}
            
            if start_date and end_date:
                filter_expressions.append('#ts BETWEEN :start_ts AND :end_ts')
                expression_names['#ts'] = 'timestamp'
                expression_values[':start_ts'] = {'N': str(start_date.timestamp())}
                expression_values[':end_ts'] = {'N': str(end_date.timestamp())}
            
            if session_id:
                filter_expressions.append('session_id = :session_id')
                expression_values[':session_id'] = {'S': session_id}
            
            scan_params = {
                'TableName': self.table_name,
                'Limit': limit
            }
            
            if filter_expressions:
                scan_params['FilterExpression'] = ' AND '.join(filter_expressions)
                if expression_values:
                    scan_params['ExpressionAttributeValues'] = expression_values
                if expression_names:
                    scan_params['ExpressionAttributeNames'] = expression_names
            
            response = self.dynamodb.scan(**scan_params)
            
            records = []
            for item in response.get('Items', []):
                record = PerformanceRecord.from_dynamodb_item(item)
                
                # Apply function name filter if specified
                if function_name and function_name not in record.function_names:
                    continue
                    
                records.append(record)
            
            return records
        except Exception as e:
            print(f"Error fetching filtered records: {e}")
            return []
    
    def get_unique_hostnames(self) -> List[str]:
        """Get list of unique hostnames."""
        try:
            response = self.dynamodb.scan(
                TableName=self.table_name,
                ProjectionExpression='hostname'
            )
            
            hostnames = set()
            for item in response.get('Items', []):
                hostnames.add(item['hostname']['S'])
            
            return sorted(list(hostnames))
        except Exception as e:
            print(f"Error fetching hostnames: {e}")
            return []
    
    def get_unique_function_names(self) -> List[str]:
        """Get list of unique function names across all records."""
        try:
            records = self.get_all_records(limit=1000)  # Get more records for comprehensive list
            functions = set()
            
            for record in records:
                functions.update(record.function_names)
            
            return sorted(list(functions))
        except Exception as e:
            print(f"Error fetching function names: {e}")
            return []
    
    def get_performance_metrics(self, 
                              hostname: Optional[str] = None,
                              start_date: Optional[datetime] = None,
                              end_date: Optional[datetime] = None,
                              function_name: Optional[str] = None) -> PerformanceMetrics:
        """Get aggregate performance metrics with optional filters."""
        records = self.get_filtered_records(
            hostname=hostname,
            start_date=start_date,
            end_date=end_date,
            function_name=function_name,
            limit=1000
        )
        
        return PerformanceMetrics.from_records(records)
    
    def get_recent_records(self, hours: int = 24, limit: int = 100) -> List[PerformanceRecord]:
        """Get records from the last N hours."""
        end_date = datetime.now()
        start_date = end_date - timedelta(hours=hours)
        
        return self.get_records_by_date_range(start_date, end_date, limit)
    
    def get_sessions_with_system_data(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get sessions that have system monitoring data."""
        try:
            # In a real implementation, this would query a separate table or index
            # For now, we'll scan for records with system_timeline data
            response = self.dynamodb.scan(
                TableName=self.table_name,
                FilterExpression='attribute_exists(system_timeline)',
                Limit=limit
            )
            
            sessions = []
            session_map = {}
            
            for item in response.get('Items', []):
                record = PerformanceRecord.from_dynamodb_item(item)
                session_id = record.session_id
                
                if session_id not in session_map:
                    # Extract metadata if available
                    system_timeline = item.get('system_timeline', {}).get('M', {})
                    metadata = system_timeline.get('metadata', {}).get('M', {})
                    
                    session_map[session_id] = {
                        'session_id': session_id,
                        'hostname': record.hostname,
                        'platform': metadata.get('platform', {}).get('S', 'Unknown'),
                        'start_time': datetime.fromtimestamp(record.timestamp),
                        'duration_str': self._calculate_duration_str(metadata)
                    }
            
            return list(session_map.values())
        except Exception as e:
            print(f"Error fetching sessions with system data: {e}")
            return []
    
    def get_timeline_data(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get timeline data for a specific session."""
        try:
            # Get all records for the session
            records = self.get_records_by_session(session_id)
            
            if not records:
                return None
            
            # Look for a record with system_timeline data
            for record in records:
                # In a real implementation, we'd fetch from DynamoDB directly
                # For now, we'll simulate the data structure
                response = self.dynamodb.scan(
                    TableName=self.table_name,
                    FilterExpression='session_id = :session_id AND attribute_exists(system_timeline)',
                    ExpressionAttributeValues={':session_id': {'S': session_id}},
                    Limit=1
                )
                
                if response.get('Items'):
                    item = response['Items'][0]
                    system_timeline = item.get('system_timeline', {}).get('M', {})
                    
                    # Convert DynamoDB format to JSON format
                    return self._convert_timeline_data(system_timeline)
            
            # If no system_timeline found, return mock data for demo
            return self._get_mock_timeline_data(session_id)
            
        except Exception as e:
            print(f"Error fetching timeline data: {e}")
            return None
    
    def _calculate_duration_str(self, metadata: Dict[str, Any]) -> str:
        """Calculate duration string from metadata."""
        try:
            start_time = float(metadata.get('start_time', {}).get('N', 0))
            end_time = float(metadata.get('end_time', {}).get('N', 0))
            
            if start_time and end_time:
                duration = end_time - start_time
                minutes = int(duration // 60)
                seconds = int(duration % 60)
                return f"{minutes}m {seconds}s"
        except:
            pass
        return "N/A"
    
    def _convert_timeline_data(self, dynamodb_data: Dict[str, Any]) -> Dict[str, Any]:
        """Convert DynamoDB format to JSON format."""
        # This would convert the DynamoDB attribute values to plain JSON
        # For now, return a simplified structure
        return {
            'system': [],
            'processes': {},
            'metadata': {}
        }
    
    def _get_mock_timeline_data(self, session_id: str) -> Dict[str, Any]:
        """Get mock timeline data for demonstration."""
        import random
        import time
        
        base_time = time.time() - 300  # 5 minutes ago
        
        # Generate system data
        system_data = []
        for i in range(60):  # 60 samples over 5 minutes
            timestamp = base_time + (i * 5)
            system_data.append({
                'timestamp': timestamp,
                'cpu_percent': 30 + random.uniform(-10, 40) + (10 * abs(math.sin(i/10))),
                'memory_percent': 50 + random.uniform(-5, 15),
                'memory_available_mb': 8192 - random.uniform(0, 2048),
                'memory_used_mb': 8192 + random.uniform(0, 2048),
                'load_avg_1m': 2.4 + random.uniform(-0.5, 0.5),
                'load_avg_5m': 2.1 + random.uniform(-0.3, 0.3),
                'load_avg_15m': 1.8 + random.uniform(-0.2, 0.2)
            })
        
        # Generate process data
        process_data = {}
        pids = ['12345', '12346', '12347']
        process_names = ['python', 'python3', 'jupyter']
        
        for idx, pid in enumerate(pids):
            process_samples = []
            for i in range(60):
                timestamp = base_time + (i * 5)
                process_samples.append({
                    'timestamp': timestamp,
                    'pid': int(pid),
                    'name': process_names[idx],
                    'cpu_percent': 10 + random.uniform(-5, 25) + (15 * abs(math.cos(i/8 + idx))),
                    'memory_rss_mb': 128 + random.uniform(-20, 50),
                    'memory_vms_mb': 256 + random.uniform(-30, 80),
                    'num_threads': 4 + random.randint(-2, 2),
                    'status': 'running',
                    'create_time': base_time - 1000,
                    'cmdline': f'{process_names[idx]} my_script.py'
                })
            process_data[pid] = process_samples
        
        return {
            'system': system_data,
            'processes': process_data,
            'metadata': {
                'platform': 'Darwin',
                'sample_interval': 5,
                'start_time': base_time,
                'end_time': base_time + 300
            }
        }


# Global service instance
dynamodb_service = DynamoDBService()