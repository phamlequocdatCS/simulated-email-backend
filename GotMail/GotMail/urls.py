"""
URL configuration for GotMail project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import path
from gotmail_service.views import (
    AutoReplySettingsView,
    DarkModeToggleView,
    EmailActionView,
    EmailListView,
    Enable2FAView,
    FontSettingsView,
    ForgetPasswordView,
    LabelEmailView,
    LabelManagementView,
    LoginView,
    LogoutView,
    NotificationDetailView,
    NotificationListView,
    OtherUserProfileView,
    PasswordResetConfirmView,
    PasswordResetView,
    RegisterView,
    RequestVerificationView,
    SendEmailView,
    UserProfileView,
    ValidateTokenView,
    Verify2FAView,
    VerifyCodeView,
)

from GotMail import settings

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/login/", auth_views.LoginView.as_view(), name="login"),
    # API END POINTS
    path("auth/register/", RegisterView.as_view(), name="api_register"),
    path("auth/login/", LoginView.as_view(), name="api_login"),
    path("auth/logout/", LogoutView.as_view(), name="api_logout"),
    path("auth/validate_token/", ValidateTokenView.as_view(), name="validate_token"),
    path("user/profile/", UserProfileView.as_view(), name="api_profile"),
    path(
        "user/notifications/", NotificationListView.as_view(), name="api_notifications"
    ),
    path(
        "user/notifications/<int:pk>/",
        NotificationDetailView.as_view(),
        name="api_notification_detail",
    ),
    path("user/auto_rep/", AutoReplySettingsView.as_view(), name="api_send_mail"),
    path("user/darkmode/", DarkModeToggleView.as_view(), name="api_darkmode_toggle"),
    path("user/email_pref/", FontSettingsView.as_view(), name="api_email_pref"),
    path("user/labels/", LabelManagementView.as_view(), name="api_email_labels"),
    path("user/email_labels/", LabelEmailView.as_view(), name="api_user_email_labels"),
    path("email/send/", SendEmailView.as_view(), name="api_send_mail"),
    path("email_list/", EmailListView.as_view(), name="api_list_mail"),
    path("email/action/", EmailActionView.as_view(), name="email_action"),
    path("auth/verify/start/", RequestVerificationView.as_view(), name="verify_phone"),
    path("auth/verify/code/", VerifyCodeView.as_view(), name="verify_code"),
    path(
        "other/profile/<int:user_id>/",
        OtherUserProfileView.as_view(),
        name="api_get_other_user_profile",
    ),
    path("auth/reset_password/", PasswordResetView.as_view(), name="password_reset"),
    path(
        "auth/reset_password_confirm/",
        PasswordResetConfirmView.as_view(),
        name="password_reset_confirm",
    ),
    path("auth/forget_password/", ForgetPasswordView.as_view(), name="forget_password"),
    path("auth/2fa/", Enable2FAView.as_view(), name="enable_2fa"),
    path("auth/2fa_verify/", Verify2FAView.as_view(), name="verify_2fa"),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
