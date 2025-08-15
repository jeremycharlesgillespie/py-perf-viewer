"""
Service for managing the persistent systems registry.

HOSTNAME DUPLICATE PREVENTION:
Always use py_perf.hostname_utils.get_normalized_hostname() when working with hostnames
to prevent duplicate entries for the same machine with different hostname formats.

Common causes of duplicates:
- Using raw socket.gethostname() instead of normalized version
- Network configuration changes (DHCP/static, domain changes)
- OS hostname changes during setup or reconfiguration

If duplicates are detected, use remove_system() to mark stale entries as inactive.
"""

import boto3
import logging
import time
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from django.conf import settings
from decimal import Decimal
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)


class SystemRegistryService:
    """Service for managing persistent system registry."""
    
    def __init__(self):
        self.dynamodb = boto3.client('dynamodb', region_name=settings.AWS_DEFAULT_REGION)
        self.table_resource = boto3.resource('dynamodb', region_name=settings.AWS_DEFAULT_REGION).Table('py-perf-systems-registry')
        self.table_name = 'py-perf-systems-registry'
        
        # Threshold for considering a system offline (in seconds)
        self.offline_threshold = 360  # 6 minutes
    
    def get_all_systems(self) -> List[Dict[str, Any]]:
        """Get all registered systems from the registry."""
        try:
            response = self.table_resource.scan(
                FilterExpression='active = :active',
                ExpressionAttributeValues={':active': True}
            )
            
            systems = []
            current_time = time.time()
            
            for item in response.get('Items', []):
                # Convert Decimal to float for JSON serialization
                system = {
                    'hostname': item.get('hostname'),
                    'last_seen': float(item.get('last_seen', 0)),
                    'last_update': item.get('last_update'),
                    'cpu_percent': float(item.get('cpu_percent', 0)),
                    'memory_percent': float(item.get('memory_percent', 0)),
                    'platform': item.get('platform', 'Unknown'),
                    'first_seen': float(item.get('first_seen', 0)),
                    'active': item.get('active', True)
                }
                
                # Calculate status based on last_seen
                time_diff = current_time - system['last_seen']
                if time_diff < self.offline_threshold:
                    system['status'] = 'online'
                elif time_diff < self.offline_threshold * 10:  # Less than 1 hour
                    system['status'] = 'offline'
                else:
                    system['status'] = 'stale'
                
                # Add human-readable time
                if system['last_seen'] > 0:
                    system['last_update_human'] = datetime.fromtimestamp(system['last_seen']).strftime('%Y-%m-%d %H:%M:%S')
                else:
                    system['last_update_human'] = 'Never'
                
                systems.append(system)
            
            # Handle pagination if needed
            while 'LastEvaluatedKey' in response:
                response = self.table_resource.scan(
                    FilterExpression='active = :active',
                    ExpressionAttributeValues={':active': True},
                    ExclusiveStartKey=response['LastEvaluatedKey']
                )
                
                for item in response.get('Items', []):
                    system = {
                        'hostname': item.get('hostname'),
                        'last_seen': float(item.get('last_seen', 0)),
                        'last_update': item.get('last_update'),
                        'cpu_percent': float(item.get('cpu_percent', 0)),
                        'memory_percent': float(item.get('memory_percent', 0)),
                        'platform': item.get('platform', 'Unknown'),
                        'first_seen': float(item.get('first_seen', 0)),
                        'active': item.get('active', True)
                    }
                    
                    # Calculate status
                    time_diff = current_time - system['last_seen']
                    if time_diff < self.offline_threshold:
                        system['status'] = 'online'
                    elif time_diff < self.offline_threshold * 10:
                        system['status'] = 'offline'
                    else:
                        system['status'] = 'stale'
                    
                    # Add human-readable time
                    if system['last_seen'] > 0:
                        system['last_update_human'] = datetime.fromtimestamp(system['last_seen']).strftime('%Y-%m-%d %H:%M:%S')
                    else:
                        system['last_update_human'] = 'Never'
                    
                    systems.append(system)
            
            logger.info(f"Retrieved {len(systems)} systems from registry")
            return systems
            
        except Exception as e:
            logger.error(f"Failed to retrieve systems from registry: {e}")
            return []
    
    def remove_system(self, hostname: str) -> bool:
        """Mark a system as inactive in the registry (soft delete)."""
        try:
            self.table_resource.update_item(
                Key={'hostname': hostname},
                UpdateExpression='SET active = :inactive, removed_at = :removed_at',
                ExpressionAttributeValues={
                    ':inactive': False,
                    ':removed_at': datetime.utcnow().isoformat()
                }
            )
            logger.info(f"Marked system {hostname} as inactive")
            return True
            
        except Exception as e:
            logger.error(f"Failed to remove system {hostname}: {e}")
            return False
    
    def reactivate_system(self, hostname: str) -> bool:
        """Reactivate a previously removed system."""
        try:
            self.table_resource.update_item(
                Key={'hostname': hostname},
                UpdateExpression='SET active = :active REMOVE removed_at',
                ExpressionAttributeValues={
                    ':active': True
                }
            )
            logger.info(f"Reactivated system {hostname}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to reactivate system {hostname}: {e}")
            return False
    
    def get_system_info(self, hostname: str) -> Optional[Dict[str, Any]]:
        """Get information for a specific system from the registry."""
        try:
            response = self.table_resource.get_item(
                Key={'hostname': hostname}
            )
            
            if 'Item' not in response:
                return None
            
            item = response['Item']
            current_time = time.time()
            
            system = {
                'hostname': item.get('hostname'),
                'last_seen': float(item.get('last_seen', 0)),
                'last_update': item.get('last_update'),
                'cpu_percent': float(item.get('cpu_percent', 0)),
                'memory_percent': float(item.get('memory_percent', 0)),
                'platform': item.get('platform', 'Unknown'),
                'first_seen': float(item.get('first_seen', 0)),
                'active': item.get('active', True)
            }
            
            # Calculate status
            time_diff = current_time - system['last_seen']
            if time_diff < self.offline_threshold:
                system['status'] = 'online'
            elif time_diff < self.offline_threshold * 10:
                system['status'] = 'offline'
            else:
                system['status'] = 'stale'
            
            return system
            
        except Exception as e:
            logger.error(f"Failed to get system info for {hostname}: {e}")
            return None


# Create singleton instance
system_registry_service = SystemRegistryService()