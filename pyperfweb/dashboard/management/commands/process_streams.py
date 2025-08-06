"""
Django management command to process DynamoDB Streams messages from SQS.
Run with: python manage.py process_streams
"""

import json
import logging
import signal
import sys
import time
from typing import Dict, Any

import boto3
from django.core.management.base import BaseCommand
from django.conf import settings
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Process DynamoDB Streams messages from SQS and send to WebSocket clients'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.running = True
        self.sqs_client = None
        self.channel_layer = None
        
        # Set up signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)

    def add_arguments(self, parser):
        parser.add_argument(
            '--queue-url',
            type=str,
            help='SQS Queue URL (overrides DYNAMODB_STREAMS_QUEUE_URL setting)',
        )
        parser.add_argument(
            '--poll-interval',
            type=int,
            default=10,
            help='Polling interval in seconds (default: 10)',
        )
        parser.add_argument(
            '--max-messages',
            type=int,
            default=10,
            help='Maximum messages to receive per poll (default: 10)',
        )

    def signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully."""
        self.stdout.write(f"\nReceived signal {signum}. Shutting down gracefully...")
        self.running = False

    def handle(self, *args, **options):
        """Main command handler."""
        self.stdout.write("🚀 Starting DynamoDB Streams processor...")
        
        # Initialize SQS client
        try:
            self.sqs_client = boto3.client('sqs')
            self.stdout.write("✅ SQS client initialized")
        except Exception as e:
            self.stderr.write(f"❌ Failed to initialize SQS client: {e}")
            return

        # Get queue URL
        queue_url = options['queue_url'] or settings.DYNAMODB_STREAMS_QUEUE_URL
        if not queue_url:
            self.stderr.write("❌ No SQS queue URL provided. Set DYNAMODB_STREAMS_QUEUE_URL or use --queue-url")
            return

        self.stdout.write(f"📡 Using SQS queue: {queue_url}")

        # Initialize channel layer
        self.channel_layer = get_channel_layer()
        if not self.channel_layer:
            self.stderr.write("❌ No channel layer configured")
            return

        self.stdout.write("✅ WebSocket channel layer initialized")
        
        # Start processing loop
        self.stdout.write("🔄 Starting message processing loop...")
        self.process_messages(
            queue_url=queue_url,
            poll_interval=options['poll_interval'],
            max_messages=options['max_messages']
        )

    def process_messages(self, queue_url: str, poll_interval: int, max_messages: int):
        """Main message processing loop."""
        while self.running:
            try:
                # Receive messages from SQS
                response = self.sqs_client.receive_message(
                    QueueUrl=queue_url,
                    MaxNumberOfMessages=max_messages,
                    WaitTimeSeconds=min(poll_interval, 20),  # Long polling (max 20s)
                    MessageAttributeNames=['All']
                )

                messages = response.get('Messages', [])
                if messages:
                    self.stdout.write(f"📨 Received {len(messages)} messages")
                    
                    for message in messages:
                        self.process_single_message(message, queue_url)
                else:
                    # No messages received, continue polling
                    continue

            except KeyboardInterrupt:
                self.stdout.write("\n⏹️  Interrupted by user")
                break
            except Exception as e:
                self.stderr.write(f"❌ Error receiving messages: {e}")
                time.sleep(5)  # Wait before retrying

        self.stdout.write("✅ Gracefully shut down")

    def process_single_message(self, message: Dict[str, Any], queue_url: str):
        """Process a single SQS message."""
        try:
            # Parse message body
            message_body = json.loads(message['Body'])
            message_type = message_body.get('type', 'unknown')
            hostname = message_body.get('hostname', 'unknown')
            
            self.stdout.write(f"🔍 Processing {message_type} for {hostname}")
            
            # Send to appropriate WebSocket groups
            if message_type == 'metrics_update':
                self.send_metrics_update(message_body)
            elif message_type == 'host_offline':
                self.send_host_offline(message_body)
            elif message_type == 'cache_invalidation':
                self.send_cache_invalidation(message_body)
            else:
                self.stderr.write(f"⚠️  Unknown message type: {message_type}")

            # Delete processed message from SQS
            self.sqs_client.delete_message(
                QueueUrl=queue_url,
                ReceiptHandle=message['ReceiptHandle']
            )
            
            self.stdout.write(f"✅ Processed and deleted message for {hostname}")

        except json.JSONDecodeError:
            self.stderr.write("❌ Invalid JSON in SQS message")
        except Exception as e:
            self.stderr.write(f"❌ Error processing message: {e}")

    def send_metrics_update(self, message_data: Dict[str, Any]):
        """Send metrics update to WebSocket clients."""
        hostname = message_data.get('hostname')
        
        # Send to dashboard group (all connected dashboard clients)
        async_to_sync(self.channel_layer.group_send)(
            'dashboard_updates',
            {
                'type': 'metrics_update',
                'hostname': hostname,
                'metrics': message_data.get('metrics', {}),
                'timestamp': message_data.get('timestamp'),
                'event_type': message_data.get('event_type', 'unknown')
            }
        )
        
        # Send to hostname-specific group (system detail page clients)
        async_to_sync(self.channel_layer.group_send)(
            f'system_detail_{hostname}',
            {
                'type': 'metrics_update',
                'hostname': hostname,
                'metrics': message_data.get('metrics', {}),
                'timestamp': message_data.get('timestamp'),
                'event_type': message_data.get('event_type', 'unknown')
            }
        )

    def send_host_offline(self, message_data: Dict[str, Any]):
        """Send host offline notification to WebSocket clients."""
        hostname = message_data.get('hostname')
        
        # Send to dashboard group
        async_to_sync(self.channel_layer.group_send)(
            'dashboard_updates',
            {
                'type': 'host_offline',
                'hostname': hostname,
                'timestamp': message_data.get('updated_at')
            }
        )
        
        # Send to hostname-specific group
        async_to_sync(self.channel_layer.group_send)(
            f'system_detail_{hostname}',
            {
                'type': 'host_offline',
                'hostname': hostname,
                'timestamp': message_data.get('updated_at')
            }
        )

    def send_cache_invalidation(self, message_data: Dict[str, Any]):
        """Send cache invalidation to WebSocket clients."""
        hostname = message_data.get('hostname')
        
        # Send to dashboard group
        async_to_sync(self.channel_layer.group_send)(
            'dashboard_updates',
            {
                'type': 'cache_invalidation',
                'hostname': hostname,
                'cache_keys': message_data.get('cache_keys', [])
            }
        )
        
        # Send to hostname-specific group
        async_to_sync(self.channel_layer.group_send)(
            f'system_detail_{hostname}',
            {
                'type': 'cache_invalidation',
                'hostname': hostname,
                'cache_keys': message_data.get('cache_keys', [])
            }
        )