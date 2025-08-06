"""
Service for reading system performance data from DynamoDB.
"""

import boto3
import json
import logging
import time
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from django.conf import settings
from django.core.cache import cache
from botocore.exceptions import ClientError

try:
    from .metadata_service import metadata_service
    HAS_METADATA_SERVICE = True
except Exception as e:
    logger = logging.getLogger(__name__)
    logger.warning(f"Metadata service not available: {e}")
    HAS_METADATA_SERVICE = False


logger = logging.getLogger(__name__)


class SystemDataService:
    """Service class for reading system performance data from DynamoDB."""
    
    def __init__(self):
        self.dynamodb = boto3.client('dynamodb', region_name=settings.AWS_DEFAULT_REGION)
        self.table_resource = boto3.resource('dynamodb', region_name=settings.AWS_DEFAULT_REGION).Table('py-perf-system')
        self.table_name = 'py-perf-system'
    
    def get_recent_system_data(self, hostname: Optional[str] = None, hours: int = 24, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get recent system performance data."""
        try:
            cutoff_time = (datetime.now() - timedelta(hours=hours)).timestamp()
            
            # Build scan parameters (convert to Decimal for DynamoDB)
            from decimal import Decimal
            scan_params = {
                'FilterExpression': '#ts > :cutoff_time',
                'ExpressionAttributeNames': {'#ts': 'timestamp'},
                'ExpressionAttributeValues': {':cutoff_time': Decimal(str(cutoff_time))}
            }
            
            # Add hostname filter if provided
            if hostname:
                scan_params['FilterExpression'] += ' AND hostname = :hostname'
                scan_params['ExpressionAttributeValues'][':hostname'] = hostname
            
            # Add limit if provided
            if limit:
                scan_params['Limit'] = limit
                
            # Handle pagination to get records (with limit if specified)
            records = []
            response = self.table_resource.scan(**scan_params)
            records.extend(response.get('Items', []))
            
            # Continue scanning if there are more items and no limit specified
            while 'LastEvaluatedKey' in response and not limit:
                scan_params['ExclusiveStartKey'] = response['LastEvaluatedKey']
                response = self.table_resource.scan(**scan_params)
                records.extend(response.get('Items', []))
            
            # Parse metrics_data JSON for each record and convert Decimals to floats
            parsed_records = []
            for record in records:
                if 'metrics_data' in record:
                    try:
                        record['parsed_metrics'] = json.loads(record['metrics_data'])
                        # Convert Decimal fields to float for easier handling
                        if 'timestamp' in record:
                            record['timestamp'] = float(record['timestamp'])
                        if 'start_time' in record:
                            record['start_time'] = float(record['start_time'])
                        if 'end_time' in record:
                            record['end_time'] = float(record['end_time'])
                        parsed_records.append(record)
                    except json.JSONDecodeError:
                        logger.warning(f"Failed to parse metrics_data for record {record.get('id')}")
            
            # Sort by timestamp
            parsed_records.sort(key=lambda x: x.get('timestamp', 0))
            
            logger.info(f"Retrieved {len(parsed_records)} system data records")
            return parsed_records
            
        except Exception as e:
            logger.error(f"Failed to retrieve system data: {e}")
            return []
    
    def get_system_hostnames(self) -> List[str]:
        """Get list of unique hostnames with system data."""
        try:
            response = self.table_resource.scan(
                ProjectionExpression='hostname'
            )
            
            hostnames = set()
            for item in response.get('Items', []):
                if 'hostname' in item:
                    hostnames.add(item['hostname'])
            
            return sorted(list(hostnames))
        except Exception as e:
            logger.error(f"Error fetching system hostnames: {e}")
            return []
    
    def get_system_metrics_for_hostname(self, hostname: str, hours: int = 24) -> Dict[str, Any]:
        """Get aggregated system metrics for a specific hostname."""
        # Limit to 300 records for performance (should cover most use cases)
        records = self.get_recent_system_data(hostname=hostname, hours=hours, limit=300)
        
        # Get the absolute first time this hostname appeared (not filtered by time range)
        first_seen_timestamp = self._get_first_seen_timestamp(hostname)
        
        if not records:
            return {
                'hostname': hostname,
                'total_records': 0,
                'time_range': {
                    'start': first_seen_timestamp,
                    'end': 0
                } if first_seen_timestamp else None,
                'current_cpu': 0,
                'current_memory': 0,
                'avg_cpu': 0,
                'avg_memory': 0,
                'max_cpu': 0,
                'max_memory': 0,
                'last_seen': 0,
                'first_seen': first_seen_timestamp,
                'timeline_data': []
            }
        
        # Get latest metrics from the most recent record
        latest_record = max(records, key=lambda x: x.get('timestamp', 0))
        latest_metrics = latest_record.get('parsed_metrics', [])
        
        # Get the very latest system data point
        current_cpu = 0
        current_memory = 0
        if latest_metrics:
            latest_system_data = None
            latest_timestamp = 0
            
            # Find the most recent system data point
            for metric in latest_metrics:
                metric_timestamp = metric.get('timestamp', 0)
                if metric_timestamp > latest_timestamp and 'system' in metric:
                    latest_timestamp = metric_timestamp
                    latest_system_data = metric['system']
            
            if latest_system_data:
                current_cpu = latest_system_data.get('cpu_percent', 0)
                current_memory = latest_system_data.get('memory_percent', 0)
        
        # Aggregate metrics for historical analysis
        cpu_values = []
        memory_values = []
        timeline_data = []
        
        for record in records:
            metrics = record.get('parsed_metrics', [])
            record_timestamp = record.get('timestamp', 0)
            
            for metric in metrics:
                system_data = metric.get('system', {})
                if system_data:
                    cpu_percent = system_data.get('cpu_percent', 0)
                    memory_percent = system_data.get('memory_percent', 0)
                    
                    cpu_values.append(cpu_percent)
                    memory_values.append(memory_percent)
                    
                    timeline_data.append({
                        'timestamp': metric.get('timestamp', record_timestamp),
                        'cpu_percent': cpu_percent,
                        'memory_percent': memory_percent,
                        'memory_available_mb': system_data.get('memory_available_mb', 0),
                        'memory_used_mb': system_data.get('memory_used_mb', 0)
                    })
        
        # Sort timeline data
        timeline_data.sort(key=lambda x: x['timestamp'])
        
        return {
            'hostname': hostname,
            'total_records': len(records),
            'time_range': {
                'start': first_seen_timestamp,  # Absolute first time seen
                'end': records[-1].get('timestamp')  # Latest time in current range
            } if records else None,
            'current_cpu': current_cpu,  # Latest real-time value
            'current_memory': current_memory,  # Latest real-time value
            'avg_cpu': sum(cpu_values) / len(cpu_values) if cpu_values else 0,
            'avg_memory': sum(memory_values) / len(memory_values) if memory_values else 0,
            'max_cpu': max(cpu_values) if cpu_values else 0,
            'max_memory': max(memory_values) if memory_values else 0,
            'last_seen': latest_record.get('timestamp', 0) if latest_record.get('timestamp', 0) > 0 else None,
            'first_seen': first_seen_timestamp,  # Absolute first time seen
            'is_online': (time.time() - latest_record.get('timestamp', 0)) < 120,  # Online if last seen within 2 minutes
            'timeline_data': timeline_data[-200:]  # Last 200 data points for charts
        }
    
    def _get_first_seen_timestamp(self, hostname: str) -> Optional[float]:
        """Get the absolute first timestamp when a hostname appeared in the database."""
        # Check cache first
        cache_key = f"first_seen_{hostname}"
        cached_timestamp = cache.get(cache_key)
        
        if cached_timestamp is not None:
            logger.debug(f"Using cached first_seen timestamp for {hostname}: {cached_timestamp}")
            return cached_timestamp
        
        logger.info(f"Cache miss for first_seen timestamp - querying for {hostname}")
        
        # Try metadata service first (fastest)
        if HAS_METADATA_SERVICE:
            try:
                first_seen = metadata_service.get_first_seen(hostname)
                if first_seen is not None:
                    # Cache for 30 days since first_seen never changes
                    cache.set(cache_key, first_seen, timeout=2592000)
                    logger.info(f"Found first_seen via metadata service for {hostname}: {first_seen}")
                    return first_seen
            except Exception as e:
                logger.warning(f"Metadata service query failed: {e}")
        
        try:
            from decimal import Decimal
            
            # Try to use GSI if it exists
            try:
                # Query using the hostname-timestamp-index GSI
                response = self.table_resource.query(
                    IndexName='hostname-timestamp-index',
                    KeyConditionExpression='hostname = :hostname',
                    ExpressionAttributeValues={':hostname': hostname},
                    ProjectionExpression='#ts',
                    ExpressionAttributeNames={'#ts': 'timestamp'},
                    Limit=1,  # We only need the first record
                    ScanIndexForward=True  # Sort ascending by timestamp
                )
                
                items = response.get('Items', [])
                if items:
                    first_seen = float(items[0]['timestamp'])
                    # Cache for 30 days since first_seen never changes
                    cache.set(cache_key, first_seen, timeout=2592000)  # 30 days
                    logger.info(f"Found first_seen via GSI for {hostname}: {first_seen}")
                    return first_seen
                    
            except ClientError as e:
                if e.response['Error']['Code'] == 'ValidationException':
                    # GSI doesn't exist, fall back to scan
                    logger.warning("GSI not found, falling back to table scan")
                else:
                    raise
            
            # Fallback: Scan for all records for this hostname (expensive!)
            logger.warning(f"Using table scan for {hostname} - consider creating GSI")
            scan_params = {
                'FilterExpression': 'hostname = :hostname',
                'ExpressionAttributeValues': {':hostname': hostname},
                'ProjectionExpression': '#ts',
                'ExpressionAttributeNames': {'#ts': 'timestamp'}
            }
            
            response = self.table_resource.scan(**scan_params)
            items = response.get('Items', [])
            
            # Continue scanning if there are more items
            while 'LastEvaluatedKey' in response:
                scan_params['ExclusiveStartKey'] = response['LastEvaluatedKey']
                response = self.table_resource.scan(**scan_params)
                items.extend(response.get('Items', []))
            
            if not items:
                # Cache the None result for a shorter time to avoid repeated scans
                cache.set(cache_key, None, timeout=3600)  # 1 hour
                return None
            
            # Find the minimum timestamp
            timestamps = [float(item['timestamp']) for item in items if 'timestamp' in item]
            first_seen = min(timestamps) if timestamps else None
            
            if first_seen:
                # Cache for 30 days since first_seen never changes
                cache.set(cache_key, first_seen, timeout=2592000)  # 30 days
                logger.info(f"Cached first_seen timestamp for {hostname}: {first_seen}")
            
            return first_seen
            
        except Exception as e:
            logger.error(f"Failed to get first seen timestamp for {hostname}: {e}")
            # Cache the failure for a short time to avoid immediate retries
            cache.set(cache_key, None, timeout=300)  # 5 minutes
            return None
    
    def invalidate_first_seen_cache(self, hostname: str) -> None:
        """Invalidate the cached first_seen timestamp for a hostname."""
        cache_key = f"first_seen_{hostname}"
        cache.delete(cache_key)
        logger.info(f"Invalidated first_seen cache for {hostname}")
    
    def get_system_dashboard_data(self) -> Dict[str, Any]:
        """Get dashboard overview data for all system hosts."""
        try:
            # Get recent data for all hosts (limit to 200 records for performance)
            all_records = self.get_recent_system_data(hours=24, limit=200)
            
            if not all_records:
                return {
                    'total_hosts': 0,
                    'total_records': 0,
                    'hosts_summary': [],
                    'recent_activity': []
                }
            
            # Group by hostname
            hosts_data = {}
            for record in all_records:
                hostname = record.get('hostname', 'unknown')
                if hostname not in hosts_data:
                    hosts_data[hostname] = []
                hosts_data[hostname].append(record)
            
            # Create summary for each host
            hosts_summary = []
            for hostname, host_records in hosts_data.items():
                summary = self.get_system_metrics_for_hostname(hostname, hours=24)
                max_timestamp = max(r.get('timestamp', 0) for r in host_records)
                summary['last_seen'] = max_timestamp if max_timestamp > 0 else None
                summary['is_online'] = (time.time() - max_timestamp) < 120 if max_timestamp > 0 else False  # Online if last seen within 2 minutes
                hosts_summary.append(summary)
            
            # Sort by last seen (timestamps)
            hosts_summary.sort(key=lambda x: x.get('last_seen') or 0, reverse=True)
            
            return {
                'total_hosts': len(hosts_data),
                'total_records': len(all_records),
                'hosts_summary': hosts_summary,
                'recent_activity': all_records[-10:]  # Last 10 records
            }
            
        except Exception as e:
            logger.error(f"Failed to get system dashboard data: {e}")
            return {
                'total_hosts': 0,
                'total_records': 0,
                'hosts_summary': [],
                'recent_activity': []
            }
    
    def test_connection(self) -> bool:
        """Test connection to system data table."""
        try:
            response = self.dynamodb.describe_table(TableName=self.table_name)
            table_status = response['Table']['TableStatus']
            return table_status == 'ACTIVE'
        except Exception as e:
            logger.error(f"System data table connection test failed: {e}")
            return False


# Global service instance
system_data_service = SystemDataService()