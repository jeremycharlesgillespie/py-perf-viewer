import json
import boto3
from decimal import Decimal

dynamodb = boto3.resource('dynamodb')
metadata_table = dynamodb.Table('py-perf-metadata')

def lambda_handler(event, context):
    """
    Process DynamoDB Stream events and update metadata table.
    This ensures first_seen is always accurate and fast to query.
    """
    for record in event['Records']:
        if record['eventName'] == 'INSERT':
            new_image = record['dynamodb']['NewImage']
            hostname = new_image['hostname']['S']
            timestamp = float(new_image['timestamp']['N'])
            
            # Try to update only if this is an earlier timestamp
            try:
                response = metadata_table.get_item(Key={'hostname': hostname})
                
                if 'Item' not in response:
                    # First time seeing this host
                    metadata_table.put_item(Item={
                        'hostname': hostname,
                        'first_seen': Decimal(str(timestamp)),
                        'last_updated': Decimal(str(timestamp)),
                        'total_records': 1
                    })
                    print(f"Created metadata for new host: {hostname}")
                else:
                    # Update if this timestamp is earlier
                    current_first_seen = float(response['Item']['first_seen'])
                    if timestamp < current_first_seen:
                        metadata_table.update_item(
                            Key={'hostname': hostname},
                            UpdateExpression='SET first_seen = :ts',
                            ExpressionAttributeValues={':ts': Decimal(str(timestamp))}
                        )
                        print(f"Updated earlier first_seen for {hostname}")
                        
            except Exception as e:
                print(f"Error updating metadata for {hostname}: {e}")
    
    return {'statusCode': 200, 'body': 'Success'}
