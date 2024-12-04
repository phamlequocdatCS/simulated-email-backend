"""
ASGI config for GotMail project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.1/howto/deployment/asgi/
"""

import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
import gotmail_service.routing  # Import the email_app routing

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "GotMail.settings")

# Initialize Django ASGI application early to ensure the AppRegistry
# is populated before importing code that may import ORM models.

application = ProtocolTypeRouter(
    {
        "http": get_asgi_application(),  # Use the existing django_asgi_app
        "websocket": AuthMiddlewareStack(  # Wrap with AuthMiddlewareStack
            URLRouter(
                gotmail_service.routing.websocket_urlpatterns  # Include the email_app websocket routing
            )
        ),
    }
)
