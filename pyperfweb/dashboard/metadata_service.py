"""
Service for managing host metadata in a separate DynamoDB table.
This provides extremely fast lookups for static information like first_seen timestamps.
"""

import boto3
import logging
from typing import Optional, Dict, Any
from decimal import Decimal
from django.conf import settings
from django.core.cache import cache
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)


class MetadataService:
    """Service for managing host metadata in DynamoDB."""
    
    def __init__(self):
        self.dynamodb = boto3.resource('dynamodb', region_name=settings.AWS_DEFAULT_REGION)
        self.table = self.dynamodb.Table('py-perf-metadata')
        self.table_name = 'py-perf-metadata'
    
    def get_host_metadata(self, hostname: str) -> Optional[Dict[str, Any]]:
        """Get metadata for a specific hostname."""
        # Check cache first
        cache_key = f"metadata_{hostname}"
        cached_data = cache.get(cache_key)
        
        if cached_data is not None:
            logger.debug(f"Using cached metadata for {hostname}")
            return cached_data
        
        try:
            response = self.table.get_item(Key={'hostname': hostname})
            
            if 'Item' in response:
                item = response['Item']
                metadata = {
                    'hostname': item.get('hostname'),
                    'first_seen': float(item.get('first_seen', 0)),
                    'last_updated': float(item.get('last_updated', 0)),
                    'total_records': int(item.get('total_records', 0))
                }
                
                # Cache for 24 hours since metadata changes infrequently
                cache.set(cache_key, metadata, timeout=86400)
                logger.info(f"Retrieved and cached metadata for {hostname}")
                return metadata
            else:
                # Cache None result for 1 hour
                cache.set(cache_key, None, timeout=3600)
                return None
                
        except ClientError as e:
            logger.error(f"Error retrieving metadata for {hostname}: {e}")
            return None
    
    def get_first_seen(self, hostname: str) -> Optional[float]:
        """Get just the first_seen timestamp for a hostname."""
        metadata = self.get_host_metadata(hostname)
        return metadata.get('first_seen') if metadata else None
    
    def update_host_metadata(self, hostname: str, first_seen: float = None, 
                           last_updated: float = None, increment_count: bool = False) -> bool:
        """Update metadata for a hostname."""
        try:
            update_expression_parts = []
            expression_values = {}
            
            if first_seen is not None:
                update_expression_parts.append('first_seen = :fs')
                expression_values[':fs'] = Decimal(str(first_seen))
            
            if last_updated is not None:
                update_expression_parts.append('last_updated = :lu')
                expression_values[':lu'] = Decimal(str(last_updated))
            
            if increment_count:
                update_expression_parts.append('total_records = total_records + :inc')
                expression_values[':inc'] = 1
            
            if update_expression_parts:
                self.table.update_item(
                    Key={'hostname': hostname},
                    UpdateExpression='SET ' + ', '.join(update_expression_parts),
                    ExpressionAttributeValues=expression_values
                )
                
                # Invalidate cache
                cache_key = f"metadata_{hostname}"
                cache.delete(cache_key)
                
                logger.info(f"Updated metadata for {hostname}")
                return True
                
        except ClientError as e:
            logger.error(f"Error updating metadata for {hostname}: {e}")
            
        return False
    
    def create_host_metadata(self, hostname: str, first_seen: float) -> bool:
        """Create initial metadata entry for a new hostname."""
        try:
            self.table.put_item(
                Item={
                    'hostname': hostname,
                    'first_seen': Decimal(str(first_seen)),
                    'last_updated': Decimal(str(first_seen)),
                    'total_records': 1
                },
                ConditionExpression='attribute_not_exists(hostname)'
            )
            
            # Invalidate cache
            cache_key = f"metadata_{hostname}"
            cache.delete(cache_key)
            
            logger.info(f"Created metadata for new host: {hostname}")
            return True
            
        except ClientError as e:
            if e.response['Error']['Code'] == 'ConditionalCheckFailedException':
                logger.debug(f"Metadata already exists for {hostname}")
            else:
                logger.error(f"Error creating metadata for {hostname}: {e}")
                
        return False
    
    def test_connection(self) -> bool:
        """Test connection to metadata table."""
        try:
            response = self.dynamodb.meta.client.describe_table(TableName=self.table_name)
            return response['Table']['TableStatus'] == 'ACTIVE'
        except Exception as e:
            logger.error(f"Metadata table connection test failed: {e}")
            return False


# Global service instance
metadata_service = MetadataService()