from django.contrib import admin
from .models import User, Email, Label, Notification

admin.site.register(User)
admin.site.register(Email)
admin.site.register(Label)
admin.site.register(Notification)
