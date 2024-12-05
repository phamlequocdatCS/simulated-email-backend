from django.contrib import admin
from .models import User, Email, Label, Notification, UserProfile, UserSettings

admin.site.register(User)
admin.site.register(Email)
admin.site.register(Label)
admin.site.register(Notification)
admin.site.register(UserProfile)
admin.site.register(UserSettings)
