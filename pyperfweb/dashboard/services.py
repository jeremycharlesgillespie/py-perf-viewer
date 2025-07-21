import boto3
from boto3.dynamodb.conditions import Key, Attr
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from django.conf import settings
from .models import PerformanceRecord, PerformanceMetrics


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


# Global service instance
dynamodb_service = DynamoDBService()