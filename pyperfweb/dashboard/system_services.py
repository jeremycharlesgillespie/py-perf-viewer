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

try:
    from .metrics_compression import decompress_metrics_data
    HAS_COMPRESSION = True
except ImportError:
    logger = logging.getLogger(__name__)
    logger.warning("Compression module not available - compressed records will be skipped")
    HAS_COMPRESSION = False
    def decompress_metrics_data(data):
        return json.loads(data) if isinstance(data, str) else data


logger = logging.getLogger(__name__)


class SystemDataService:
    """Service class for reading system performance data from DynamoDB."""
    
    def __init__(self):
        self.dynamodb = boto3.client('dynamodb', region_name=settings.AWS_DEFAULT_REGION)
        # Use py-perf-system table for system metrics (different from app performance data)
        self.table_resource = boto3.resource('dynamodb', region_name=settings.AWS_DEFAULT_REGION).Table('py-perf-system')
        self.table_name = 'py-perf-system'
    
    def get_recent_system_data(self, hostname: Optional[str] = None, hours: int = 24, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get recent system performance data using GSI for better performance."""
        try:
            cutoff_time = (datetime.now() - timedelta(hours=hours)).timestamp()
            from decimal import Decimal
            
            records = []
            
            if hostname:
                # First try to get the most recent record using the latest marker
                latest_record_id = None
                latest_timestamp = self.get_latest_timestamp_for_host(hostname)
                
                if latest_timestamp and latest_timestamp > cutoff_time:
                    # Try to get the latest record ID from the marker
                    try:
                        import hashlib
                        hostname_hash = int(hashlib.md5(f'latest_{hostname}'.encode()).hexdigest()[:8], 16)
                        marker_response = self.table_resource.get_item(
                            Key={'id': hostname_hash},
                            ConsistentRead=True
                        )
                        if 'Item' in marker_response:
                            latest_record_id = marker_response['Item'].get('latest_record_id')
                    except Exception as e:
                        logger.debug(f"Could not get latest record ID from marker: {e}")
                
                # Use consistent read scan for fresh data with full record attributes
                records = self._scan_fallback(hostname, cutoff_time, limit)
                
                # If we have a latest record ID, try to fetch it directly
                if latest_record_id and latest_timestamp:
                    try:
                        latest_response = self.table_resource.get_item(
                            Key={'id': int(latest_record_id)},
                            ConsistentRead=True
                        )
                        if 'Item' in latest_response:
                            latest_item = latest_response['Item']
                            # Add to records if not already present
                            if not any(r.get('id') == latest_record_id for r in records):
                                records.insert(0, latest_item)  # Add at beginning
                                logger.info(f"Added latest record {latest_record_id} via direct lookup")
                    except Exception as e:
                        logger.debug(f"Could not fetch latest record directly: {e}")
                
                logger.debug(f"Using scan with {len(records)} records for {hostname}")
            else:
                # For all hosts, we need to scan or query each known hostname
                # First get list of hostnames, then query each one
                hostnames = self.get_system_hostnames()
                for host in hostnames:
                    host_records = self.get_recent_system_data(hostname=host, hours=hours, limit=None)
                    records.extend(host_records)
                
                # Sort all records by timestamp and apply limit
                records.sort(key=lambda x: x.get('timestamp', 0), reverse=True)
                if limit:
                    records = records[:limit]
            
            # Parse metrics_data JSON for all records
            parsed_records = []
            for record in records:
                if 'metrics_data' in record and 'timestamp' in record:
                    try:
                        # Convert timestamp
                        record_timestamp = float(record['timestamp'])
                        
                        # Check if this is a compressed record
                        if record.get('compressed', False):
                            if HAS_COMPRESSION:
                                record['parsed_metrics'] = decompress_metrics_data(record['metrics_data'])
                                logger.debug(f"Successfully decompressed metrics for record {record.get('id')}")
                            else:
                                logger.warning(f"Skipping compressed record {record.get('id')} - compression module not available")
                                continue
                        else:
                            # Handle uncompressed (legacy) records
                            record['parsed_metrics'] = json.loads(record['metrics_data'])
                        
                        # Convert Decimal fields to float for easier handling
                        record['timestamp'] = record_timestamp
                        if 'start_time' in record:
                            record['start_time'] = float(record['start_time'])
                        if 'end_time' in record:
                            record['end_time'] = float(record['end_time'])
                        parsed_records.append(record)
                        
                    except (json.JSONDecodeError, Exception) as e:
                        logger.warning(f"Failed to parse metrics_data for record {record.get('id')}: {e}")
            
            logger.info(f"Retrieved {len(parsed_records)} system data records")
            return parsed_records
            
        except Exception as e:
            logger.error(f"Failed to retrieve system data: {e}")
            return []
    
    def _scan_fallback(self, hostname: Optional[str], cutoff_time: float, limit: Optional[int]) -> List[Dict[str, Any]]:
        """Aggressive scan method to find the freshest data across table segments."""
        try:
            from decimal import Decimal
            import boto3
            
            # Create a fresh DynamoDB connection to avoid any caching/pooling issues
            fresh_dynamodb = boto3.resource('dynamodb', region_name=self.table_resource.meta.client.meta.region_name)
            fresh_table = fresh_dynamodb.Table(self.table_name)
            
            # For real-time data, scan without time filter and sort in Python
            # This ensures we get the absolute latest records regardless of partitioning
            scan_params = {
                'Limit': 300,  # Balanced limit for performance vs coverage
                'ConsistentRead': True
            }
            
            # Add hostname filter only (no time filter to avoid missing fresh data)  
            if hostname:
                scan_params['FilterExpression'] = 'hostname = :hostname'
                scan_params['ExpressionAttributeValues'] = {':hostname': hostname}
            
            all_records = []
            response = fresh_table.scan(**scan_params)
            all_records.extend(response.get('Items', []))
            
            # Do aggressive parallel scans across more segments for maximum coverage
            # This scans different partitions simultaneously to find fresh data
            for segment in range(8):  # Scan 8 parallel segments for balance of coverage vs speed
                parallel_scan_params = scan_params.copy()
                parallel_scan_params['Segment'] = segment
                parallel_scan_params['TotalSegments'] = 16
                parallel_scan_params['Limit'] = 50  # Smaller limit per segment for better performance
                
                try:
                    parallel_response = fresh_table.scan(**parallel_scan_params)
                    parallel_records = parallel_response.get('Items', [])
                    all_records.extend(parallel_records)
                    logger.debug(f"Parallel segment {segment} found {len(parallel_records)} records")
                except Exception as e:
                    logger.debug(f"Parallel segment {segment} failed: {e}")
            
            scan_count = 8  # Update for logging
            
            # Filter by time in Python and sort by timestamp (newest first)
            recent_records = []
            for record in all_records:
                if 'timestamp' in record:
                    try:
                        record_time = float(record['timestamp'])
                        if record_time > cutoff_time:
                            recent_records.append(record)
                    except (ValueError, TypeError):
                        continue
            
            # Sort by timestamp (newest first) and apply limit
            recent_records.sort(key=lambda x: float(x.get('timestamp', 0)), reverse=True)
            if limit:
                recent_records = recent_records[:limit]
            
            logger.info(f"Fresh connection scan: {len(recent_records)} recent records from {len(all_records)} total across {scan_count} segments")
            return recent_records
            
        except Exception as e:
            logger.error(f"Fresh connection scan failed: {e}")
            return []
    
    def get_system_hostnames(self) -> List[str]:
        """Get list of unique hostnames with system data."""
        try:
            # First try to get hostnames from latest records (fast, consistent)
            response = self.table_resource.scan(
                FilterExpression='record_type = :record_type',
                ExpressionAttributeValues={':record_type': 'latest_marker'},
                ProjectionExpression='hostname'
            )
            
            hostnames = set()
            for item in response.get('Items', []):
                if 'hostname' in item:
                    hostnames.add(item['hostname'])
            
            # If we found hostnames via latest markers, use those
            if hostnames:
                logger.debug(f"Found {len(hostnames)} hostnames via latest markers")
                return sorted(list(hostnames))
            
            # Fallback to full scan if no latest markers exist yet
            response = self.table_resource.scan(
                ProjectionExpression='hostname'
            )
            
            for item in response.get('Items', []):
                if 'hostname' in item:
                    hostnames.add(item['hostname'])
            
            return sorted(list(hostnames))
        except Exception as e:
            logger.error(f"Error fetching system hostnames: {e}")
            return []
    
    def get_latest_timestamp_for_host(self, hostname: str) -> Optional[float]:
        """Get the latest timestamp for a hostname using the latest marker (fast, consistent)."""
        try:
            # Calculate the same hash-based ID as the daemon uses
            import hashlib
            hostname_hash = int(hashlib.md5(f'latest_{hostname}'.encode()).hexdigest()[:8], 16)
            
            # Direct lookup using the predictable ID
            response = self.table_resource.get_item(
                Key={'id': hostname_hash},
                ConsistentRead=True  # Always use strong consistency for latest markers
            )
            
            if 'Item' in response:
                timestamp = float(response['Item'].get('timestamp', 0))
                logger.debug(f"Found latest timestamp for {hostname}: {timestamp}")
                return timestamp
            
            return None
        except Exception as e:
            logger.debug(f"No latest marker for {hostname}: {e}")
            return None
    
    def get_system_metrics_for_hostname(self, hostname: str, hours: int = 24) -> Dict[str, Any]:
        """Get aggregated system metrics for a specific hostname."""
        # First check for latest timestamp using fast lookup
        latest_timestamp = self.get_latest_timestamp_for_host(hostname)
        
        # Check cache for historical data (older than 10 minutes won't change)
        current_time = time.time()
        cache_boundary = current_time - 600  # 10 minutes ago
        historical_cache_key = f"historical_timeline_{hostname}_{hours}h_{int(cache_boundary // 3600)}"  # Hour-based cache key
        
        # Initialize variables
        records = []
        timeline_data = []
        
        cached_historical_data = cache.get(historical_cache_key)
        if cached_historical_data:
            logger.debug(f"Using cached historical timeline data for {hostname}")
            
            # Get only recent data (last 10 minutes) from DynamoDB
            recent_records = self.get_recent_system_data(hostname=hostname, hours=1, limit=50)
            records = recent_records  # Set records variable for later use
            recent_timeline_data = []
            
            for record in recent_records:
                if record.get('timestamp', 0) > cache_boundary:
                    metrics = record.get('parsed_metrics', [])
                    for metric in metrics:
                        system_data = metric.get('system', {})
                        if system_data and metric.get('timestamp', 0) > cache_boundary:
                            # Round to minute boundary
                            minute_timestamp = int(metric.get('timestamp', 0) // 60) * 60
                            recent_timeline_data.append({
                                'timestamp': minute_timestamp,
                                'cpu_percent': system_data.get('cpu_percent', 0),
                                'memory_percent': system_data.get('memory_percent', 0),
                                'memory_available_mb': system_data.get('memory_available_mb', 0),
                                'memory_used_mb': system_data.get('memory_used_mb', 0)
                            })
            
            # Combine cached historical data with recent data
            all_timeline_data = cached_historical_data + recent_timeline_data
            
            # Remove duplicates and sort
            seen_minutes = set()
            unique_timeline_data = []
            for data_point in sorted(all_timeline_data, key=lambda x: x['timestamp']):
                minute = data_point['timestamp']
                if minute not in seen_minutes:
                    seen_minutes.add(minute)
                    unique_timeline_data.append(data_point)
            
            timeline_data = unique_timeline_data
            logger.info(f"Used cached data + {len(recent_timeline_data)} recent points")
        else:
            logger.info(f"Cache miss for historical data - full query for {hostname}")
            # Full data retrieval (existing logic)
            records = self.get_recent_system_data(hostname=hostname, hours=hours, limit=300)
            
            # Process all timeline data when cache miss occurs
            timeline_data = []
            for record in records:
                metrics = record.get('parsed_metrics', [])
                for metric in metrics:
                    system_data = metric.get('system', {})
                    if system_data:
                        timeline_data.append({
                            'timestamp': metric.get('timestamp', record.get('timestamp', 0)),
                            'cpu_percent': system_data.get('cpu_percent', 0),
                            'memory_percent': system_data.get('memory_percent', 0),
                            'memory_available_mb': system_data.get('memory_available_mb', 0),
                            'memory_used_mb': system_data.get('memory_used_mb', 0)
                        })
            
            # Sort and filter to 1-minute intervals
            timeline_data.sort(key=lambda x: x['timestamp'])
            filtered_timeline_data = []
            last_minute = None
            
            for data_point in timeline_data:
                timestamp = data_point['timestamp']
                minute_timestamp = int(timestamp // 60) * 60
                
                if last_minute != minute_timestamp:
                    data_point['timestamp'] = minute_timestamp
                    filtered_timeline_data.append(data_point)
                    last_minute = minute_timestamp
            
            timeline_data = filtered_timeline_data
            
            # Cache historical portion (older than 10 minutes) for future use
            historical_data = [dp for dp in timeline_data if dp['timestamp'] < cache_boundary]
            if historical_data:
                cache.set(historical_cache_key, historical_data, timeout=86400)  # Cache for 24 hours
                logger.info(f"Cached {len(historical_data)} historical data points")
        
        # Get the absolute first time this hostname appeared (not filtered by time range)
        first_seen_timestamp = self._get_first_seen_timestamp(hostname)
        
        if not records and not timeline_data:
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
        
        # Get current CPU/Memory values from timeline data (most recent point)
        current_cpu = 0
        current_memory = 0
        if timeline_data:
            latest_point = max(timeline_data, key=lambda x: x['timestamp'])
            current_cpu = latest_point.get('cpu_percent', 0)
            current_memory = latest_point.get('memory_percent', 0)
        
        # Aggregate metrics for historical analysis from timeline data
        cpu_values = [dp['cpu_percent'] for dp in timeline_data]
        memory_values = [dp['memory_percent'] for dp in timeline_data]
        
        # Calculate last seen timestamp
        last_seen_timestamp = 0
        if timeline_data:
            last_seen_timestamp = max(dp['timestamp'] for dp in timeline_data)
        elif records:
            last_seen_timestamp = max(r.get('timestamp', 0) for r in records)
            
        return {
            'hostname': hostname,
            'total_records': len(records) if records else len(timeline_data),
            'time_range': {
                'start': first_seen_timestamp,  # Absolute first time seen
                'end': last_seen_timestamp  # Latest time in current range
            } if last_seen_timestamp > 0 else None,
            'current_cpu': current_cpu,  # Latest real-time value
            'current_memory': current_memory,  # Latest real-time value
            'avg_cpu': sum(cpu_values) / len(cpu_values) if cpu_values else 0,
            'avg_memory': sum(memory_values) / len(memory_values) if memory_values else 0,
            'max_cpu': max(cpu_values) if cpu_values else 0,
            'max_memory': max(memory_values) if memory_values else 0,
            'last_seen': last_seen_timestamp if last_seen_timestamp > 0 else None,
            'first_seen': first_seen_timestamp,  # Absolute first time seen
            'is_online': (time.time() - last_seen_timestamp) < 360 if last_seen_timestamp > 0 else False,  # Online if last seen within 6 minutes
            'timeline_data': timeline_data[-200:] if timeline_data else []  # Last 200 data points for charts
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
            # Get recent data for all hosts (need enough records to find fresh data)
            all_records = self.get_recent_system_data(hours=24, limit=100)
            
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
                
                # Use the fast latest timestamp lookup first
                latest_timestamp = self.get_latest_timestamp_for_host(hostname)
                if latest_timestamp:
                    # Use the fast, consistent latest marker timestamp
                    summary['last_seen'] = latest_timestamp
                    summary['is_online'] = (time.time() - latest_timestamp) < 360
                    logger.debug(f"Using latest marker for {hostname}: {latest_timestamp}")
                else:
                    # Fallback to max timestamp from records
                    max_timestamp = max(r.get('timestamp', 0) for r in host_records)
                    summary['last_seen'] = max_timestamp if max_timestamp > 0 else None
                    summary['is_online'] = (time.time() - max_timestamp) < 360 if max_timestamp > 0 else False
                
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