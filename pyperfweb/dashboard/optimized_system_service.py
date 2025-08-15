"""
Optimized Django service for reading system data from the new v2 table structure.
"""

import boto3
import logging
import time
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from django.conf import settings
from django.core.cache import cache
from botocore.exceptions import ClientError

try:
    from .registry_service import system_registry_service
    HAS_REGISTRY = True
except ImportError:
    HAS_REGISTRY = False
    system_registry_service = None

logger = logging.getLogger(__name__)


class OptimizedSystemService:
    """Service for reading from the optimized py-perf-system-v2 table."""
    
    def __init__(self):
        self.dynamodb = boto3.client('dynamodb', region_name=settings.AWS_DEFAULT_REGION)
        self.table_resource = boto3.resource('dynamodb', region_name=settings.AWS_DEFAULT_REGION).Table('py-perf-system-v2')
        self.table_name = 'py-perf-system-v2'
    
    def get_system_metrics_for_hostname(self, hostname: str, hours: int = 24) -> Dict[str, Any]:
        """Get system metrics for a hostname using optimized storage."""
        try:
            # Get recent data (already in frontend format)
            timeline_data = self._get_recent_data(hostname, hours)
            
            if not timeline_data:
                return {
                    'hostname': hostname,
                    'total_records': 0,
                    'time_range': None,
                    'current_cpu': 0,
                    'current_memory': 0,
                    'avg_cpu': 0,
                    'avg_memory': 0,
                    'max_cpu': 0,
                    'max_memory': 0,
                    'last_seen': 0,
                    'first_seen': None,
                    'is_online': False,
                    'timeline_data': []
                }
            
            # Calculate metrics from timeline data
            cpu_values = [dp['cpu_percent'] for dp in timeline_data]
            memory_values = [dp['memory_percent'] for dp in timeline_data]
            timestamps = [dp['timestamp'] for dp in timeline_data]
            
            latest_point = max(timeline_data, key=lambda x: x['timestamp'])
            
            return {
                'hostname': hostname,
                'total_records': len(timeline_data),
                'time_range': {
                    'start': min(timestamps) if timestamps else 0,
                    'end': max(timestamps) if timestamps else 0
                },
                'current_cpu': latest_point.get('cpu_percent', 0),
                'current_memory': latest_point.get('memory_percent', 0),
                'avg_cpu': sum(cpu_values) / len(cpu_values) if cpu_values else 0,
                'avg_memory': sum(memory_values) / len(memory_values) if memory_values else 0,
                'max_cpu': max(cpu_values) if cpu_values else 0,
                'max_memory': max(memory_values) if memory_values else 0,
                'last_seen': latest_point.get('timestamp', 0),
                'first_seen': self._get_first_seen_from_registry(hostname),
                'is_online': (time.time() - latest_point.get('timestamp', 0)) < 360,  # 6 minutes
                'timeline_data': timeline_data
            }
            
        except Exception as e:
            logger.error(f"Failed to get optimized metrics for {hostname}: {e}")
            return self._empty_response(hostname)
    
    def _get_recent_data(self, hostname: str, hours: int) -> List[Dict[str, Any]]:
        """Get recent data from optimized table structure."""
        try:
            current_time = time.time()
            start_time = current_time - (hours * 3600)
            
            # Generate list of hour partitions to query (use UTC to match daemon)
            from datetime import timezone
            start_dt = datetime.fromtimestamp(start_time, tz=timezone.utc)
            current_dt = datetime.fromtimestamp(current_time, tz=timezone.utc)
            
            all_records = []
            
            # Query each hour partition
            hour_dt = start_dt.replace(minute=0, second=0, microsecond=0)
            while hour_dt <= current_dt:
                hostname_hour = f"{hostname}#{hour_dt.strftime('%Y-%m-%d-%H')}"
                
                try:
                    # Query this hour's data
                    response = self.table_resource.query(
                        KeyConditionExpression='hostname_hour = :hostname_hour AND minute_timestamp >= :start_time',
                        ExpressionAttributeValues={
                            ':hostname_hour': hostname_hour,
                            ':start_time': int(start_time)
                        }
                    )
                    
                    hour_records = response.get('Items', [])
                    all_records.extend(hour_records)
                    
                except ClientError as e:
                    if e.response['Error']['Code'] != 'ResourceNotFoundException':
                        logger.warning(f"Error querying hour partition {hostname_hour}: {e}")
                
                # Move to next hour
                hour_dt = hour_dt + timedelta(hours=1)
            
            # Convert DynamoDB items to regular dicts and sort
            records = []
            for item in all_records:
                record = self._convert_from_dynamodb_item(item)
                records.append(record)
            
            # Sort by timestamp
            records.sort(key=lambda x: x['timestamp'])
            
            logger.info(f"Retrieved {len(records)} optimized records for {hostname}")
            return records
            
        except Exception as e:
            logger.error(f"Failed to retrieve optimized data for {hostname}: {e}")
            return []
    
    def _convert_from_dynamodb_item(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """Convert DynamoDB item back to regular dict."""
        from decimal import Decimal
        
        record = {}
        for key, value in item.items():
            if isinstance(value, Decimal):
                record[key] = float(value)
            else:
                record[key] = value
        
        return record
    
    def _get_first_seen_timestamp(self, hostname: str) -> Optional[float]:
        """Get first seen timestamp (cached)."""
        cache_key = f"first_seen_v2_{hostname}"
        cached_timestamp = cache.get(cache_key)
        
        if cached_timestamp is not None:
            return cached_timestamp
        
        try:
            # Query earliest record across all partitions
            # For now, do a limited search across recent days
            current_time = time.time()
            search_days = 30  # Search back 30 days max
            
            earliest_timestamp = None
            
            for days_back in range(search_days):
                search_dt = datetime.fromtimestamp(current_time - (days_back * 86400))
                
                for hour in range(24):
                    search_hour_dt = search_dt.replace(hour=hour, minute=0, second=0, microsecond=0)
                    hostname_hour = f"{hostname}#{search_hour_dt.strftime('%Y-%m-%d-%H')}"
                    
                    try:
                        response = self.table_resource.query(
                            KeyConditionExpression='hostname_hour = :hostname_hour',
                            ExpressionAttributeValues={
                                ':hostname_hour': hostname_hour
                            },
                            ScanIndexForward=True,  # Ascending order (earliest first)
                            Limit=1
                        )
                        
                        items = response.get('Items', [])
                        if items:
                            timestamp = float(items[0]['minute_timestamp'])
                            if earliest_timestamp is None or timestamp < earliest_timestamp:
                                earliest_timestamp = timestamp
                    
                    except ClientError:
                        continue  # Skip missing partitions
            
            # Cache the result
            if earliest_timestamp:
                cache.set(cache_key, earliest_timestamp, timeout=86400)  # Cache for 24 hours
            
            return earliest_timestamp
            
        except Exception as e:
            logger.error(f"Failed to get first seen timestamp for {hostname}: {e}")
            return None
    
    def _get_first_seen_from_registry(self, hostname: str) -> Optional[float]:
        """Get first_seen timestamp from registry service (fast)."""
        try:
            if HAS_REGISTRY and system_registry_service:
                system_info = system_registry_service.get_system_info(hostname)
                if system_info:
                    return system_info.get('first_seen')
            
            # Fallback: try to get from cache first
            cache_key = f"first_seen_v2_{hostname}"
            cached_timestamp = cache.get(cache_key)
            if cached_timestamp is not None:
                return cached_timestamp
                
            logger.warning(f"No registry data or cache for {hostname}, first_seen will be None")
            return None
            
        except Exception as e:
            logger.warning(f"Failed to get first_seen from registry for {hostname}: {e}")
            return None
    
    def get_system_dashboard_data(self) -> Dict[str, Any]:
        """Get dashboard overview data using optimized storage."""
        try:
            # If registry is available, use it for the system list
            if HAS_REGISTRY and system_registry_service:
                # Get all systems from registry
                registry_systems = system_registry_service.get_all_systems()
                
                hosts_summary = []
                total_records = 0
                
                for system in registry_systems:
                    hostname = system['hostname']
                    
                    # Get latest data point from v2 table
                    latest_data = self._get_latest_data_point(hostname)
                    
                    if latest_data:
                        # Use fresh data from v2 table
                        host_summary = {
                            'hostname': hostname,
                            'current_cpu': latest_data.get('cpu_percent', 0),
                            'current_memory': latest_data.get('memory_percent', 0),
                            'last_seen': latest_data.get('timestamp', 0),
                            'is_online': (time.time() - latest_data.get('timestamp', 0)) < 360,
                            'first_seen': system.get('first_seen'),
                            'platform': system.get('platform', 'Unknown'),
                            'status': system.get('status', 'unknown'),
                            'registry_last_seen': system.get('last_seen', 0)
                        }
                    else:
                        # No recent data in v2 table, use registry info
                        host_summary = {
                            'hostname': hostname,
                            'current_cpu': system.get('cpu_percent', 0),
                            'current_memory': system.get('memory_percent', 0),
                            'last_seen': system.get('last_seen', 0),
                            'is_online': system.get('status') == 'online',
                            'first_seen': system.get('first_seen', None),
                            'platform': system.get('platform', 'Unknown'),
                            'status': system.get('status', 'unknown'),
                            'registry_last_seen': system.get('last_seen', 0)
                        }
                    
                    hosts_summary.append(host_summary)
                    total_records += 1
                
                logger.info(f"Using registry: found {len(registry_systems)} systems")
                
            else:
                # Fallback to scanning for hostnames
                hostnames = self._get_all_hostnames()
                
                hosts_summary = []
                total_records = 0
                
                for hostname in hostnames:
                    # Get latest data point for each hostname
                    latest_data = self._get_latest_data_point(hostname)
                    if latest_data:
                        host_summary = {
                            'hostname': hostname,
                            'current_cpu': latest_data.get('cpu_percent', 0),
                            'current_memory': latest_data.get('memory_percent', 0),
                            'last_seen': latest_data.get('timestamp', 0),
                            'is_online': (time.time() - latest_data.get('timestamp', 0)) < 360,
                            'first_seen': self._get_first_seen_from_registry(hostname),
                            'platform': 'Unknown',
                            'status': 'online' if (time.time() - latest_data.get('timestamp', 0)) < 360 else 'offline'
                        }
                        hosts_summary.append(host_summary)
                        total_records += 1
            
            # Sort by last seen
            hosts_summary.sort(key=lambda x: x.get('last_seen', 0), reverse=True)
            
            return {
                'total_hosts': len(hosts_summary),
                'total_records': total_records,
                'hosts_summary': hosts_summary,
                'recent_activity': []
            }
            
        except Exception as e:
            logger.error(f"Failed to get optimized dashboard data: {e}")
            return {
                'total_hosts': 0,
                'total_records': 0,
                'hosts_summary': [],
                'recent_activity': []
            }
    
    def _get_latest_data_point(self, hostname: str) -> Optional[Dict[str, Any]]:
        """Get the latest data point for a hostname."""
        try:
            current_time = time.time()
            current_dt = datetime.fromtimestamp(current_time)
            
            # Check current hour first
            hostname_hour = f"{hostname}#{current_dt.strftime('%Y-%m-%d-%H')}"
            
            response = self.table_resource.query(
                KeyConditionExpression='hostname_hour = :hostname_hour',
                ExpressionAttributeValues={
                    ':hostname_hour': hostname_hour
                },
                ScanIndexForward=False,  # Descending order (latest first)
                Limit=1
            )
            
            items = response.get('Items', [])
            if items:
                return self._convert_from_dynamodb_item(items[0])
            
            # Check previous hour if no data in current hour
            prev_hour_dt = current_dt - timedelta(hours=1)
            prev_hostname_hour = f"{hostname}#{prev_hour_dt.strftime('%Y-%m-%d-%H')}"
            
            response = self.table_resource.query(
                KeyConditionExpression='hostname_hour = :hostname_hour',
                ExpressionAttributeValues={
                    ':hostname_hour': prev_hostname_hour
                },
                ScanIndexForward=False,
                Limit=1
            )
            
            items = response.get('Items', [])
            if items:
                return self._convert_from_dynamodb_item(items[0])
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get latest data for {hostname}: {e}")
            return None
    
    def _get_all_hostnames(self) -> List[str]:
        """Get all hostnames from recent data (limited scan)."""
        try:
            hostnames = set()
            
            # Simple scan approach to find all hostnames
            try:
                response = self.table_resource.scan(
                    ProjectionExpression='hostname',
                    Limit=1000  # Reasonable limit for hostname discovery
                )
                
                for item in response.get('Items', []):
                    hostname = item.get('hostname')
                    if hostname:
                        hostnames.add(hostname)
                        
                # Continue scanning if there are more items and we haven't found enough hostnames
                while 'LastEvaluatedKey' in response and len(hostnames) < 50:
                    response = self.table_resource.scan(
                        ProjectionExpression='hostname',
                        Limit=1000,
                        ExclusiveStartKey=response['LastEvaluatedKey']
                    )
                    
                    for item in response.get('Items', []):
                        hostname = item.get('hostname')
                        if hostname:
                            hostnames.add(hostname)
                            
            except Exception as e:
                logger.error(f"Error scanning for hostnames: {e}")
            
            logger.info(f"Found {len(hostnames)} hostnames: {sorted(list(hostnames))}")
            return sorted(list(hostnames))
            
        except Exception as e:
            logger.error(f"Failed to get hostnames: {e}")
            return []
    
    def _empty_response(self, hostname: str) -> Dict[str, Any]:
        """Return empty response structure."""
        return {
            'hostname': hostname,
            'total_records': 0,
            'time_range': None,
            'current_cpu': 0,
            'current_memory': 0,
            'avg_cpu': 0,
            'avg_memory': 0,
            'max_cpu': 0,
            'max_memory': 0,
            'last_seen': 0,
            'first_seen': None,
            'is_online': False,
            'timeline_data': []
        }
    
    def test_connection(self) -> bool:
        """Test connection to optimized table."""
        try:
            response = self.dynamodb.describe_table(TableName=self.table_name)
            return response['Table']['TableStatus'] == 'ACTIVE'
        except Exception as e:
            logger.error(f"Optimized table connection test failed: {e}")
            return False


# Global service instance
optimized_system_service = OptimizedSystemService()