import json

from asgiref.sync import sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from django.contrib.auth import get_user_model
from django.utils import timezone


class EmailConsumer(AsyncWebsocketConsumer):
    active_connections = {}  # type: ignore  # {user_id: [channel_name1, channel_name2, ...]}

    async def connect(self):
        self.token = self.scope["query_string"].decode("utf-8").split("=")[1]
        self.user = await self.get_user_from_token(self.token)

        if self.user:
            self.group_name = f"user_{self.user.id}_emails"

            # Remove stale connections for this user
            stale_connections = self.active_connections.get(self.user.id, [])
            for channel in stale_connections:
                await self.channel_layer.group_discard(self.group_name, channel)
            self.active_connections[self.user.id] = []

            # Add current connection to the group and active connections
            await self.channel_layer.group_add(self.group_name, self.channel_name)
            self.active_connections[self.user.id].append(self.channel_name)

            print(f"Connected WebSocket: {self.channel_name} for {self.group_name}")
            await self.accept()
        else:
            await self.close()

    async def disconnect(self, close_code):
        if hasattr(self, "group_name"):
            try:
                print(f"Disconnecting WebSocket: {self.channel_name} for {self.group_name}")

                # Remove this connection from the group and active connections
                await self.channel_layer.group_discard(self.group_name, self.channel_name)
                self.active_connections[self.user.id].remove(self.channel_name)

                # Clean up if no active connections remain for this user
                if not self.active_connections[self.user.id]:
                    del self.active_connections[self.user.id]
            except Exception as e:
                print(e)
                

    async def email_notification(self, event):
        print(self.user)
        print(self.group_name)
        # Send email notification to the client
        print(f"Sending email notification to client: {event}")
        await self.send(
            text_data=json.dumps(
                {
                    "type": event["type"],
                    "email": event["email"],
                    "notification": event["notification"],
                }
            )
        )

    async def get_user_from_token(self, token):
        try:
            user = await sync_to_async(get_user_model().objects.get)(
                session_token=token, session_expiry__gt=timezone.now()
            )
            return user
        except get_user_model().DoesNotExist:
            return None
