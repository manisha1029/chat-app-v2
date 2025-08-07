import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from chatapp.models import *

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_name = f"room_{self.scope['url_route']['kwargs']['room_name']}"
        self.user = self.scope['url_route']['kwargs'].get('user', 'Anonymous')
        
        # Add user to the room group
        await self.channel_layer.group_add(self.room_name, self.channel_name)
        await self.accept()
        
        # Store user information in the channel layer
        await self.add_user_to_room(self.room_name, self.user)
        
        # Get current active users and send initial data
        active_users = await self.get_active_users(self.room_name)
        user_count = await self.get_user_count(self.room_name)
        
        # Send initial data to the new user
        await self.send(text_data=json.dumps({
            'type': 'user_joined',
            'user': self.user,
            'user_count': user_count,
            'active_users': active_users,
            'message': f"{self.user} joined the room"
        }))
        
        # Broadcast user joined event to other users
        await self.channel_layer.group_send(
            self.room_name,
            {
                'type': 'user_joined',
                'user': self.user,
                'room_name': self.room_name
            }
        )
        
    async def disconnect(self, close_code):
        # Remove user from room tracking before broadcasting
        await self.remove_user_from_room(self.room_name, self.user)
        
        # Broadcast user left event before removing from group
        await self.channel_layer.group_send(
            self.room_name,
            {
                'type': 'user_left',
                'user': self.user,
                'room_name': self.room_name
            }
        )
        # Remove user from the room group
        await self.channel_layer.group_discard(self.room_name, self.channel_name)

    async def receive(self, text_data):
        text_data_json = json.loads(text_data)
        message = text_data_json

        event = {
            'type': 'send_message',
            'message': message,
        }

        await self.channel_layer.group_send(self.room_name, event)

    async def send_message(self, event):
        data = event['message']
        await self.create_message(data=data)

        response_data = {
            'sender': data['sender'],
            'message': data['message']
        }
        await self.send(text_data=json.dumps({'message': response_data}))

    async def user_joined(self, event):
        """Handle user joined event and broadcast updated user count and list"""
        user_count = await self.get_user_count(event['room_name'])
        active_users = await self.get_active_users(event['room_name'])
        
        await self.send(text_data=json.dumps({
            'type': 'user_joined',
            'user': event['user'],
            'user_count': user_count,
            'active_users': active_users,
            'message': f"{event['user']} joined the room"
        }))

    async def user_left(self, event):
        """Handle user left event and broadcast updated user count and list"""
        user_count = await self.get_user_count(event['room_name'])
        active_users = await self.get_active_users(event['room_name'])
        
        await self.send(text_data=json.dumps({
            'type': 'user_left',
            'user': event['user'],
            'user_count': user_count,
            'active_users': active_users,
            'message': f"{event['user']} left the room"
        }))

    @database_sync_to_async
    def get_user_count(self, room_name):
        """Get the number of users currently in the room"""
        return len(self.channel_layer.groups.get(room_name, {}))
    
    @database_sync_to_async
    def get_active_users(self, room_name):
        """Get the list of active users in the room"""
        # Get users from our custom tracking
        if hasattr(self.channel_layer, '_room_users') and room_name in self.channel_layer._room_users:
            return list(self.channel_layer._room_users[room_name])
        return []
    
    @database_sync_to_async
    def add_user_to_room(self, room_name, user):
        """Add user to room tracking"""
        # Initialize room users tracking if it doesn't exist
        if not hasattr(self.channel_layer, '_room_users'):
            self.channel_layer._room_users = {}
        
        if room_name not in self.channel_layer._room_users:
            self.channel_layer._room_users[room_name] = set()
        
        self.channel_layer._room_users[room_name].add(user)
    
    @database_sync_to_async
    def remove_user_from_room(self, room_name, user):
        """Remove user from room tracking"""
        if hasattr(self.channel_layer, '_room_users'):
            if room_name in self.channel_layer._room_users:
                self.channel_layer._room_users[room_name].discard(user)
                # Clean up empty room
                if not self.channel_layer._room_users[room_name]:
                    del self.channel_layer._room_users[room_name]
        
    @database_sync_to_async
    def create_message(self, data):
        get_room_by_name = Room.objects.get(room_name=data['room_name'])
        
        if not Message.objects.filter(message=data['message']).exists():
            new_message = Message(room=get_room_by_name, sender=data['sender'], message=data['message'])
            new_message.save()  
        