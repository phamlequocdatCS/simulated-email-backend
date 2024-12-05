from typing import Any, Dict

from django.contrib.auth import login, logout
from django.core.mail import EmailMessage
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import generics, permissions, serializers, status, viewsets
from rest_framework.authentication import BaseAuthentication
from rest_framework.decorators import action
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.generics import (
    CreateAPIView,
    ListAPIView,
    RetrieveAPIView,
    RetrieveUpdateDestroyAPIView,
)
from rest_framework.pagination import PageNumberPagination
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import (
    Email,
    Label,
    Notification,
    User,
    UserProfile,
    UserSettings,
)
from .phone_verify import send_verification_code, verify_code
from .serializers import (
    AutoReplySettingsSerializer,
    CreateEmailSerializer,
    EmailSerializer,
    Enable2FASerializer,
    FontSettingsSerializer,
    ForgetPasswordSerializer,
    LabelSerializer,
    LoginSerializer,
    NotificationSerializer,
    OtherUserProfileSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetSerializer,
    PhoneNumberSerializer,
    UserProfileSerializer,
    UserRegisterSerializer,
    UserSerializer,
    VerificationCodeSerializer,
)


class SessionTokenAuthentication(BaseAuthentication):
    """
    Custom authentication class for session token-based authentication.
    """

    def authenticate(self, request):
        session_token = request.headers.get("Authorization")
        if not session_token:
            return None

        try:
            user = User.objects.get(
                session_token=session_token, session_expiry__gt=timezone.now()
            )
            return (user, None)
        except User.DoesNotExist:
            raise AuthenticationFailed("Invalid or expired token")


class BaseUserSettingsView(APIView):
    """
    Base class for handling user settings with common authentication and error handling.
    """

    authentication_classes = [SessionTokenAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def get_or_create_user_settings(self):
        """
        Get or create UserSettings for the authenticated user.

        Returns:
            UserSettings: User settings object
        """
        return UserSettings.objects.get_or_create(user=self.request.user)[0]


    def handle_settings_update(
        self,
        serializer_class: serializers.ModelSerializer,
        data: Dict[str, Any],
        partial: bool = True,
    ) -> Response:
        """
        Generic method to update user settings with error handling.

        Args:
            serializer_class: Serializer to use for validation
            data: Data to update
            partial: Whether to allow partial updates

        Returns:
            Response with updated settings or error
        """
        try:
            user_settings = self.get_or_create_user_settings()
            if user_settings:
                serializer = serializer_class(user_settings, data=data, partial=partial)

                if serializer.is_valid():
                    serializer.save()
                    return Response(serializer.data)

                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            return Response(
                {"error": "Unable to update settings", "details": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class UserRegistrationService:
    """
    Service class to handle user registration logic.
    """

    @staticmethod
    def create_user_resources(user):
        """
        Create associated resources for a new user.

        Args:
            user: Newly created user object
        """
        UserProfile.objects.create(user=user)
        UserSettings.objects.create(user=user)

        default_labels = [
            {"name": "Important", "color": "#FF0000"},
            {"name": "Personal", "color": "#00FF00"},
            {"name": "Work", "color": "#0000FF"},
        ]
        for label_data in default_labels:
            Label.objects.create(user=user, **label_data)


class RegisterView(APIView):
    """
    View for user registration.
    """

    permission_classes = [permissions.AllowAny]

    def post(self, request):
        """
        Handle user registration process.
        """
        serializer = UserRegisterSerializer(data=request.data)

        try:
            if serializer.is_valid(raise_exception=True):
                user = serializer.save()
                UserRegistrationService.create_user_resources(user)
                login(request, user)
                return Response(
                    UserSerializer(user).data, status=status.HTTP_201_CREATED
                )

        except serializers.ValidationError as e:
            return Response(e.detail, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class LoginView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        # Convert phone number to string to ensure compatibility
        request_data = request.data.copy()
        request_data["phone_number"] = str(request_data.get("phone_number", ""))

        serializer = LoginSerializer(data=request_data, context={"request": request})

        try:
            if serializer.is_valid(raise_exception=True):
                user = serializer.validated_data["user"]

                # Check if 2FA is enabled
                try:
                    user_profile = UserProfile.objects.get(user=user)
                    if user_profile.two_factor_enabled:
                        # Generate and send 2FA code
                        user.generate_verification_code()

                        try:
                            # Send verification email
                            email = create_2fa_email(
                                request, user, user.email, user.verification_code
                            )
                            email.send(fail_silently=False)

                            return Response(
                                {
                                    "requires_2fa": True,
                                    "phone_number": user.phone_number,
                                },
                                status=status.HTTP_206_PARTIAL_CONTENT,
                            )
                        except Exception as email_error:
                            print(f"2FA email sending failed: {email_error}")
                            return Response(
                                {"detail": f"Failed to send verification code, {email_error}"},
                                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            )

                except UserProfile.DoesNotExist:
                    pass

                # Regular login flow
                user.generate_session_token()
                login(request, user)
                return Response(
                    {
                        "user": UserSerializer(user).data,
                        "session_token": user.session_token,
                    },
                    status=status.HTTP_200_OK,
                )

        except serializer.ValidationError as e:
            # More detailed error handling
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LogoutView(APIView):
    """
    View for user logout.
    """

    permission_classes = [permissions.AllowAny]

    def post(self, request):
        """
        Handle user logout process.
        """
        session_token = request.data.get("session_token") or request.headers.get(
            "Authorization"
        )
        if session_token:
            try:
                user = User.objects.get(
                    session_token=session_token, session_expiry__gt=timezone.now()
                )
                user.session_token = None
                user.session_expiry = None
                user.save()
            except User.DoesNotExist:
                pass

        logout(request)
        return Response(
            {"message": "Successfully logged out."}, status=status.HTTP_200_OK
        )


class ValidateTokenView(APIView):
    """
    View for validating session token.
    """

    permission_classes = [permissions.AllowAny]

    def post(self, request):
        """
        Validate session token.
        """
        session_token = request.data.get("session_token")
        try:
            user = User.objects.get(
                session_token=session_token, session_expiry__gt=timezone.now()
            )
            return Response(
                {"user": UserSerializer(user).data, "message": "Token is valid"},
                status=status.HTTP_200_OK,
            )
        except User.DoesNotExist:
            return Response(
                {"message": "Invalid or expired token"},
                status=status.HTTP_401_UNAUTHORIZED,
            )


class UserProfileView(RetrieveUpdateDestroyAPIView):
    """
    View for retrieving, updating, and deleting user profile.
    """

    queryset = UserProfile.objects.all()
    serializer_class = UserProfileSerializer
    authentication_classes = [SessionTokenAuthentication]
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def get_object(self):
        """
        Override get_object to return the profile of the authenticated user.
        """
        return get_object_or_404(UserProfile, user=self.request.user)

    def update(self, request, *args, **kwargs):
        """
        Update user profile and user details.
        """
        partial = kwargs.pop("partial", False)
        instance = self.get_object()

        user_data = {
            "first_name": request.data.get("first_name"),
            "last_name": request.data.get("last_name"),
            "email": request.data.get("email"),
        }
        if request.user.email != request.data.get("email"):
            if User.objects.filter(email=request.data.get("email")).exists():
                return Response(
                    {"error": "Email is already registered."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        user_data = {k: v for k, v in user_data.items() if v is not None}

        if user_data:
            user_serializer = UserSerializer(request.user, data=user_data, partial=True)
            user_serializer.is_valid(raise_exception=True)
            user_serializer.save()

        profile_data = {
            "bio": request.data.get("bio"),
            "birthdate": request.data.get("birthdate"),
        }

        if "profile_picture" in request.FILES:
            profile_data["profile_picture"] = request.FILES["profile_picture"]

        profile_data = {k: v for k, v in profile_data.items() if v is not None}

        serializer = self.get_serializer(instance, data=profile_data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        return Response(
            {"user": UserSerializer(request.user).data, "profile": serializer.data}
        )


class AutoReplySettingsView(BaseUserSettingsView):
    """
    View for handling auto-reply settings.
    """

    def get(self, request):
        """
        Retrieve current auto-reply settings.
        """
        user_settings = self.get_or_create_user_settings()
        serializer = AutoReplySettingsSerializer(user_settings)
        return Response(serializer.data)

    def put(self, request):
        """
        Update auto-reply settings.
        """
        return self.handle_settings_update(AutoReplySettingsSerializer, request.data)

    def patch(self, request):
        """
        Toggle auto-reply on/off.
        """
        try:
            user_settings = self.get_or_create_user_settings()
            user_settings.auto_reply_enabled = not user_settings.auto_reply_enabled

            if user_settings.auto_reply_enabled:
                user_settings.auto_reply_start_date = (
                    user_settings.auto_reply_start_date or timezone.now()
                )
                user_settings.auto_reply_end_date = (
                    user_settings.auto_reply_end_date
                    or timezone.now() + timezone.timedelta(days=30)
                )

            user_settings.save()
            serializer = AutoReplySettingsSerializer(user_settings)
            return Response(serializer.data)

        except Exception as e:
            return Response(
                {"error": "Unable to toggle auto-reply", "details": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class FontSettingsView(BaseUserSettingsView):
    """
    View for handling font settings.
    """

    def get(self, request):
        """
        Retrieve current font settings.
        """
        user_settings = self.get_or_create_user_settings()
        serializer = FontSettingsSerializer(user_settings)
        return Response(serializer.data)

    def put(self, request):
        """
        Update font settings.
        """
        return self.handle_settings_update(FontSettingsSerializer, request.data)


class DarkModeToggleView(BaseUserSettingsView):
    """
    View for handling dark mode settings.
    """

    def get(self, request):
        """
        Retrieve current dark mode setting.
        """
        user_settings = self.get_or_create_user_settings()
        return Response({"dark_mode": user_settings.dark_mode})

    def patch(self, request):
        """
        Set dark mode setting.
        """
        dark_mode = request.data.get("dark_mode")

        if dark_mode is None:
            return Response(
                {"error": "dark_mode field is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user_settings = self.get_or_create_user_settings()
        user_settings.dark_mode = dark_mode
        user_settings.save()

        return Response({"dark_mode": user_settings.dark_mode})


class SendEmailView(CreateAPIView):
    serializer_class = CreateEmailSerializer
    authentication_classes = [SessionTokenAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def create(self, request, *args, **kwargs):
        # Handle email creation and send
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.save()

        # Send response
        response_serializer = EmailSerializer(email, context={"request": request})
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)


class EmailListView(ListAPIView):
    """
    API endpoint for listing emails in different mailboxes.
    """

    serializer_class = EmailSerializer
    authentication_classes = [SessionTokenAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """
        Retrieve emails based on mailbox type.
        """
        user = self.request.user
        mailbox = self.request.query_params.get("mailbox", "inbox")

        if mailbox == "inbox":
            return (
                Email.objects.filter(Q(recipients=user) | Q(cc=user) | Q(bcc=user))
                .exclude(is_trashed=True)
                .order_by("-sent_at")
            )

        elif mailbox == "sent":
            return (
                Email.objects.filter(sender=user)
                .exclude(is_trashed=True)
                .order_by("-sent_at")
            )
        elif mailbox == "starred":
            return (
                Email.objects.filter(
                    (Q(recipients=user) | Q(cc=user) | Q(bcc=user)) & Q(is_starred=True)
                )
                .exclude(is_trashed=True)
                .order_by("-sent_at")
            )

        elif mailbox == "all":
            return Email.objects.filter(
                Q(recipients=user) | Q(cc=user) | Q(bcc=user)
            ).order_by("-sent_at")

        elif mailbox == "draft":
            return Email.objects.filter(sender=user, is_draft=True).order_by("-sent_at")

        elif mailbox == "trash":
            return Email.objects.filter(
                Q(sender=user) | Q(recipients=user) | Q(cc=user) | Q(bcc=user),
                is_trashed=True,
            ).order_by("-sent_at")


class EmailActionView(APIView):
    """
    API endpoint for performing email actions like marking read, starring, trashing.
    """

    authentication_classes = [SessionTokenAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        """
        Handle different email actions.
        """
        message_id = request.data.get("message_id")
        action = request.data.get("action")
        bool_state = request.data.get("bool_state")

        try:
            email = Email.objects.get(id=message_id)

            if not email.can_view(request.user):
                return Response(
                    {"error": "You do not have permission to modify this email"},
                    status=status.HTTP_403_FORBIDDEN,
                )

            if action == "mark_read":
                email.is_read = bool_state
                email.save()
            elif action == "star":
                email.is_starred = bool_state
                email.save()
            elif action == "move_to_trash":
                email.is_trashed = bool_state
                email.save()

            serializer = EmailSerializer(email)
            return Response(serializer.data)

        except Email.DoesNotExist:
            return Response(
                {"error": "Email not found"}, status=status.HTTP_404_NOT_FOUND
            )


class LabelEmailView(APIView):
    """
    API endpoint for adding or removing labels on emails.
    """

    authentication_classes = [SessionTokenAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        """
        Handle label actions on emails.
        """
        message_id = request.data.get("message_id")
        label_id = request.data.get("label_id")
        action = request.data.get("action")

        try:
            email = get_object_or_404(Email, id=message_id)

            if not email.can_view(request.user):
                return Response(
                    {"error": "You do not have permission to modify this email."},
                    status=status.HTTP_403_FORBIDDEN,
                )

            label = Label.objects.get(user=request.user, id=label_id)

            if action == "add_label":
                if not label.emails.filter(id=email.id).exists():
                    label.emails.add(email)
                    label.save()
            elif action == "remove_label":
                if label.emails.filter(id=email.id).exists():
                    label.emails.remove(email)
                    label.save()
            else:
                return Response(
                    {
                        "error": f"Invalid action: {action}. Use 'add_label' or 'remove_label'."
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            email.save()
            serializer = EmailSerializer(email)
            return Response(serializer.data, status=status.HTTP_200_OK)

        except Email.DoesNotExist:
            return Response(
                {"error": "Email not found."}, status=status.HTTP_404_NOT_FOUND
            )
        except Label.DoesNotExist:
            return Response(
                {"error": "Label not found."}, status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {"error": f"An error occurred: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class LabelManagementView(APIView):
    """
    API endpoint for managing labels (create, update, delete).
    """

    authentication_classes = [SessionTokenAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        """
        Handle label management actions.
        """
        user = request.user
        id = request.data.get("id")
        action = request.data.get("action")

        if action == "edit":
            label = get_object_or_404(Label, user=user, id=id)
            new_name = request.data.get("new_name")
            new_color = request.data.get("new_color")

            if new_name and new_name != label.name:
                label.name = new_name
            if new_color and new_color != label.color:
                label.color = new_color

            if new_name or new_color:
                label.save()
                serializer = LabelSerializer(label)
                return Response(serializer.data, status=status.HTTP_202_ACCEPTED)
            return Response(status=status.HTTP_204_NO_CONTENT)

        elif action == "create":
            new_name = request.data.get("name")
            color = request.data.get("color")

            if Label.objects.filter(user=user, name=new_name).exists():
                return Response(
                    {"error": "Label with this name already exists"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            label = Label.objects.create(user=user, name=new_name, color=color)
            serializer = LabelSerializer(label)
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        elif action == "delete":
            label = get_object_or_404(Label, user=user, id=id)
            label.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)

        else:
            return Response(
                {"error": "Invalid action"}, status=status.HTTP_400_BAD_REQUEST
            )

    def get(self, request):
        """
        Fetch all labels for the authenticated user.
        """
        user = request.user
        labels = Label.objects.filter(user=user)
        serializer = LabelSerializer(labels, many=True)
        return Response(serializer.data)


class OtherUserProfileView(RetrieveAPIView):
    """
    View for retrieving other users' profiles.
    """

    serializer_class = OtherUserProfileSerializer
    authentication_classes = [SessionTokenAuthentication]
    permission_classes = [permissions.AllowAny]

    def get_object(self):
        user_id = self.kwargs.get("user_id")
        user = get_object_or_404(User, id=user_id)
        print("Got user")
        print(user)
        return get_object_or_404(UserProfile, user=user)

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(serializer.data)


class NotificationViewSet(viewsets.ModelViewSet):
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        # Get user's notifications
        return Notification.objects.filter(user=self.request.user)

    @action(detail=False, methods=["POST"])
    def mark_all_read(self, request):
        Notification.objects.filter(user=request.user, is_read=False).update(
            is_read=True
        )
        return Response({"status": "All notifications marked as read"})

    @action(detail=True, methods=["POST"])
    def mark_read(self, request, pk=None):
        notification = self.get_object()
        notification.is_read = True
        notification.save()
        return Response({"status": "Notification marked as read"})


class NotificationListView(generics.ListAPIView):
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [SessionTokenAuthentication]
    pagination_class = PageNumberPagination

    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user)


class NotificationDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [SessionTokenAuthentication]

    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user)


class RequestVerificationView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [SessionTokenAuthentication]

    def post(self, request):
        serializer = PhoneNumberSerializer(data=request.data)
        if serializer.is_valid():
            phone_number = serializer.validated_data["phone_number"]
            user, created = User.objects.get_or_create(phone_number=phone_number)
            send_verification_code(user)
            return Response(
                {"detail": "Verification code sent."}, status=status.HTTP_200_OK
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class VerifyCodeView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [SessionTokenAuthentication]

    def post(self, request):
        serializer = VerificationCodeSerializer(data=request.data)
        if serializer.is_valid():
            phone_number = serializer.validated_data["phone_number"]
            code = serializer.validated_data["code"]
            try:
                user = User.objects.get(phone_number=phone_number)
                if verify_code(user, code):
                    return Response(
                        {"detail": "Phone number verified successfully."},
                        status=status.HTTP_200_OK,
                    )
                else:
                    return Response(
                        {"detail": "Invalid verification code."},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
            except User.DoesNotExist:
                return Response(
                    {"detail": "User not found."}, status=status.HTTP_404_NOT_FOUND
                )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class PasswordResetView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [SessionTokenAuthentication]

    def post(self, request):
        serializer = PasswordResetSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data["email"]
            try:
                user = User.objects.get(email=email)
                user.generate_password_reset_token()
                email = create_pass_reset_email(
                    request, user, email, user.password_reset_token
                )
                email.send()
                print(email)
                return Response(
                    {"detail": "Password reset code sent."}, status=status.HTTP_200_OK
                )
            except User.DoesNotExist:
                return Response(
                    {"detail": "No user found with this email."},
                    status=status.HTTP_404_NOT_FOUND,
                )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


def create_pass_reset_email(request, user, to_email, code):
    mail_subject = "Reset your password"
    message = f"Your password reset code is: {code}"
    email = EmailMessage(subject=mail_subject, body=message, to=[to_email])
    return email


class PasswordResetConfirmView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        print(request.data)
        serializer = PasswordResetConfirmSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data["email"]
            code = serializer.validated_data["code"]
            new_password = serializer.validated_data["new_password"]
            print("confirming reset password")
            print(code)
            print(new_password)
            try:
                user = User.objects.get(email=email)
                if (
                    user.password_reset_token == code
                    and user.password_reset_expires > timezone.now()
                ):
                    user.set_password(new_password)
                    user.password_reset_token = ""
                    user.password_reset_expires = None
                    user.save()
                    return Response(
                        {"detail": "Password has been reset."},
                        status=status.HTTP_200_OK,
                    )
                else:
                    return Response(
                        {"detail": "The reset code is invalid or has expired."},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
            except User.DoesNotExist:
                return Response(
                    {"detail": "The reset code is invalid."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ForgetPasswordView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = ForgetPasswordSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data["email"]
            phone_number = serializer.validated_data["phone_number"]
            try:
                user = User.objects.get(email=email, phone_number=phone_number)
                user.generate_password_reset_token()
                email = create_pass_reset_email(
                    request, user, email, user.password_reset_token
                )
                email.send()
                return Response(
                    {"detail": "Password reset code sent."}, status=status.HTTP_200_OK
                )
            except User.DoesNotExist:
                return Response(
                    {
                        "detail": "No user found with the provided email and phone number."
                    },
                    status=status.HTTP_404_NOT_FOUND,
                )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class Enable2FAView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [SessionTokenAuthentication]

    def post(self, request):
        serializer = Enable2FASerializer(data=request.data)
        if serializer.is_valid():
            user = request.user
            user_profile = UserProfile.objects.get(user=user)
            user_profile.two_factor_enabled = True
            user_profile.save()
            return Response(
                {"detail": "Two-factor authentication enabled."},
                status=status.HTTP_200_OK,
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


def create_2fa_email(request, user, to_email, code):
    mail_subject = "2 Factor authentication"
    message = f"Your 2FA code is: {code}"
    email = EmailMessage(subject=mail_subject, body=message, to=[to_email])
    return email


class Verify2FAView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        phone_number = request.data.get("phone_number")
        verification_code = request.data.get("verification_code")

        try:
            user = User.objects.get(phone_number=phone_number)

            # Check verification code validity
            if (
                user.verification_code == verification_code
                and user.verification_code_expires
                and user.verification_code_expires > timezone.now()
            ):
                # Clear verification code after successful validation
                user.verification_code = None
                user.verification_code_expires = None

                # Generate session token and log in
                user.generate_session_token()
                login(request, user)

                return Response(
                    {
                        "user": UserSerializer(user).data,
                        "session_token": user.session_token,
                    },
                    status=status.HTTP_200_OK,
                )

            return Response(
                {"detail": "Invalid or expired verification code"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        except User.DoesNotExist:
            return Response(
                {"detail": "User not found"}, status=status.HTTP_404_NOT_FOUND
            )
