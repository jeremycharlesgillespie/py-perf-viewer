"""
WebSocket consumers for real-time dashboard updates.
"""

import json
import logging
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from typing import Dict, Any

logger = logging.getLogger(__name__)


class DashboardConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for dashboard-wide real-time updates.
    Handles connections from the main system overview page.
    """
    
    async def connect(self):
        """Accept WebSocket connection and join dashboard group."""
        self.group_name = 'dashboard_updates'
        
        # Join dashboard group
        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )
        
        await self.accept()
        logger.info(f"Dashboard WebSocket connected: {self.channel_name}")
        
        # Send initial connection confirmation
        await self.send(text_data=json.dumps({
            'type': 'connection_established',
            'message': 'Connected to dashboard updates'
        }))

    async def disconnect(self, close_code):
        """Handle WebSocket disconnection."""
        # Leave dashboard group
        await self.channel_layer.group_discard(
            self.group_name,
            self.channel_name
        )
        logger.info(f"Dashboard WebSocket disconnected: {self.channel_name}")

    async def receive(self, text_data):
        """Handle messages from WebSocket client."""
        try:
            data = json.loads(text_data)
            message_type = data.get('type')
            
            if message_type == 'ping':
                await self.send(text_data=json.dumps({
                    'type': 'pong',
                    'timestamp': data.get('timestamp')
                }))
            elif message_type == 'subscribe_all':
                # Client wants to subscribe to all host updates
                logger.info("Client subscribed to all host updates")
                await self.send(text_data=json.dumps({
                    'type': 'subscription_confirmed',
                    'scope': 'all_hosts'
                }))
            else:
                logger.warning(f"Unknown message type: {message_type}")
                
        except json.JSONDecodeError:
            logger.error("Invalid JSON received from WebSocket client")
        except Exception as e:
            logger.error(f"Error processing WebSocket message: {e}")

    # Group message handlers
    async def metrics_update(self, event):
        """Send metrics update to WebSocket client."""
        await self.send(text_data=json.dumps({
            'type': 'metrics_update',
            'hostname': event['hostname'],
            'metrics': event['metrics'],
            'timestamp': event['timestamp'],
            'event_type': event.get('event_type', 'unknown')
        }))

    async def host_offline(self, event):
        """Send host offline notification to WebSocket client."""
        await self.send(text_data=json.dumps({
            'type': 'host_offline',
            'hostname': event['hostname'],
            'timestamp': event.get('timestamp')
        }))

    async def cache_invalidation(self, event):
        """Handle cache invalidation messages."""
        await self.send(text_data=json.dumps({
            'type': 'cache_invalidation',
            'hostname': event['hostname'],
            'cache_keys': event.get('cache_keys', [])
        }))


class SystemDetailConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for system detail page real-time updates.
    Handles connections for specific hostname monitoring.
    """
    
    async def connect(self):
        """Accept WebSocket connection and join hostname-specific group."""
        self.hostname = self.scope['url_route']['kwargs']['hostname']
        self.group_name = f'system_detail_{self.hostname}'
        
        # Join hostname-specific group
        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )
        
        # Also join the general dashboard group for broader updates
        await self.channel_layer.group_add(
            'dashboard_updates',
            self.channel_name
        )
        
        await self.accept()
        logger.info(f"System detail WebSocket connected for {self.hostname}: {self.channel_name}")
        
        # Send initial connection confirmation
        await self.send(text_data=json.dumps({
            'type': 'connection_established',
            'hostname': self.hostname,
            'message': f'Connected to updates for {self.hostname}'
        }))

    async def disconnect(self, close_code):
        """Handle WebSocket disconnection."""
        # Leave hostname-specific group
        await self.channel_layer.group_discard(
            self.group_name,
            self.channel_name
        )
        
        # Leave dashboard group
        await self.channel_layer.group_discard(
            'dashboard_updates',
            self.channel_name
        )
        
        logger.info(f"System detail WebSocket disconnected for {self.hostname}: {self.channel_name}")

    async def receive(self, text_data):
        """Handle messages from WebSocket client."""
        try:
            data = json.loads(text_data)
            message_type = data.get('type')
            
            if message_type == 'ping':
                await self.send(text_data=json.dumps({
                    'type': 'pong',
                    'hostname': self.hostname,
                    'timestamp': data.get('timestamp')
                }))
            elif message_type == 'subscribe_hostname':
                # Client confirming subscription to this hostname
                logger.info(f"Client subscribed to updates for {self.hostname}")
                await self.send(text_data=json.dumps({
                    'type': 'subscription_confirmed',
                    'hostname': self.hostname,
                    'scope': 'hostname_specific'
                }))
            else:
                logger.warning(f"Unknown message type: {message_type}")
                
        except json.JSONDecodeError:
            logger.error("Invalid JSON received from WebSocket client")
        except Exception as e:
            logger.error(f"Error processing WebSocket message: {e}")

    # Group message handlers (same as DashboardConsumer but filtered for hostname)
    async def metrics_update(self, event):
        """Send metrics update if it matches our hostname."""
        if event.get('hostname') == self.hostname:
            await self.send(text_data=json.dumps({
                'type': 'metrics_update',
                'hostname': event['hostname'],
                'metrics': event['metrics'],
                'timestamp': event['timestamp'],
                'event_type': event.get('event_type', 'unknown')
            }))

    async def host_offline(self, event):
        """Send host offline notification if it matches our hostname."""
        if event.get('hostname') == self.hostname:
            await self.send(text_data=json.dumps({
                'type': 'host_offline',
                'hostname': event['hostname'],
                'timestamp': event.get('timestamp')
            }))

    async def cache_invalidation(self, event):
        """Handle cache invalidation for our hostname."""
        if event.get('hostname') == self.hostname:
            await self.send(text_data=json.dumps({
                'type': 'cache_invalidation',
                'hostname': event['hostname'],
                'cache_keys': event.get('cache_keys', [])
            }))