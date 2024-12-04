import json

import magic
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.core.validators import FileExtensionValidator
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from .models import (
    Attachment,
    Email,
    Label,
    Notification,
    User,
    UserProfile,
    UserSettings,
)


class BaseUserValidationMixin:
    """
    Mixin to provide common user-related validation methods.
    """

    def validate_unique_email(self, email):
        """
        Validate that the email is unique across the system.
        """
        if User.objects.filter(email=email).exists():
            raise serializers.ValidationError({"email": "Email is already registered."})

    def validate_unique_phone(self, phone_number):
        """
        Validate that the phone number is unique across the system.
        """
        if User.objects.filter(phone_number=phone_number).exists():
            raise serializers.ValidationError(
                {"phone_number": "Phone number is already registered."}
            )


class UserSerializer(serializers.ModelSerializer):
    profile_picture = serializers.SerializerMethodField()
    is_phone_verified = serializers.BooleanField(read_only=True)

    class Meta:
        model = User
        fields = [
            "id",
            "phone_number",
            "first_name",
            "last_name",
            "email",
            "profile_picture",
            "is_phone_verified",
        ]

    def get_profile_picture(self, obj):
        """
        Get the user's profile picture or return a default.
        """
        try:
            return (
                obj.profile.profile_picture.url
                if obj.profile.profile_picture
                else "https://storage.googleapis.com/gottenmail/dog.png"
            )
        except UserProfile.DoesNotExist:
            return "https://storage.googleapis.com/gottenmail/dog.png"


class UserProfileSerializer(serializers.ModelSerializer):
    user = serializers.PrimaryKeyRelatedField(read_only=True)
    profile_picture = serializers.ImageField(
        required=False,
        allow_null=True,
        validators=[
            FileExtensionValidator(["jpg", "jpeg", "png", "gif"]),
        ],
    )

    class Meta:
        model = UserProfile
        fields = [
            "id",
            "user",
            "profile_picture",
            "bio",
            "birthdate",
            "two_factor_enabled",
        ]

    def validate_profile_picture(self, value):
        """
        Advanced validation for profile picture upload.
        """
        if value:
            # Validate file size
            if value.size > 10 * 1024 * 1024:
                raise serializers.ValidationError("Image size should not exceed 10MB.")

            # Validate file type using python-magic
            file_mime = magic.from_buffer(value.read(2048), mime=True)
            if not file_mime.startswith("image/"):
                raise serializers.ValidationError("Only image files are allowed.")
        return value


class UserRegisterSerializer(BaseUserValidationMixin, serializers.ModelSerializer):
    password = serializers.CharField(
        write_only=True,
        required=True,
        validators=[validate_password],
        style={"input_type": "password"},
    )
    password2 = serializers.CharField(
        write_only=True, required=True, style={"input_type": "password"}
    )
    verification_code = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = User
        fields = (
            "phone_number",
            "first_name",
            "last_name",
            "email",
            "password",
            "password2",
            "verification_code",
        )

    def validate(self, attrs):
        """
        Comprehensive validation for user registration.
        """
        # Check for required fields
        required_fields = [
            "phone_number",
            "first_name",
            "last_name",
            "email",
            "password",
            "password2",
        ]

        missing_fields = [field for field in required_fields if not attrs.get(field)]

        if missing_fields:
            raise serializers.ValidationError(
                {"detail": f"Missing required fields: {', '.join(missing_fields)}"}
            )

        # Validate password match
        if attrs.get("password") != attrs.get("password2"):
            raise serializers.ValidationError(
                {"password": "Password fields didn't match."}
            )

        # Use mixin methods for unique validation
        self.validate_unique_phone(attrs.get("phone_number"))
        self.validate_unique_email(attrs.get("email"))

        return attrs

    def create(self, validated_data):
        """
        Create a new user with the validated data.
        """
        validated_data.pop("password2", None)
        validated_data.pop("verification_code", None)

        user = User.objects.create_user(
            username=validated_data["phone_number"],
            phone_number=validated_data["phone_number"],
            first_name=validated_data["first_name"],
            last_name=validated_data["last_name"],
            email=validated_data["email"],
            password=validated_data["password"],
        )

        return user


class LoginSerializer(serializers.Serializer):
    phone_number = serializers.CharField(required=True)
    password = serializers.CharField(required=True, style={"input_type": "password"})

    def validate(self, attrs):
        phone_number = attrs.get("phone_number")
        password = attrs.get("password")

        if phone_number and password:
            user = authenticate(
                request=self.context.get("request"),
                username=phone_number,
                password=password,
            )

            if not user:
                msg = _("Unable to log in with provided credentials.")
                raise serializers.ValidationError(msg, code="authorization")

        else:
            msg = _('Must include "phone_number" and "password".')
            raise serializers.ValidationError(msg, code="authorization")

        attrs["user"] = user
        return attrs


class AutoReplySettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserSettings
        fields = [
            "auto_reply_enabled",
            "auto_reply_message",
            "auto_reply_start_date",
            "auto_reply_end_date",
        ]
        extra_kwargs = {
            "auto_reply_message": {"required": False, "allow_blank": True},
            "auto_reply_from_email": {"required": False, "allow_blank": True},
        }

    def validate_auto_reply_message(self, value):
        max_length = 500  # Example max length
        if len(value) > max_length:
            raise serializers.ValidationError(
                f"Auto-reply message cannot exceed {max_length} characters."
            )
        return value

    def validate(self, data):
        # Ensure message is provided when enabling auto-reply
        if data.get("auto_reply_enabled", False) and not data.get("auto_reply_message"):
            raise serializers.ValidationError(
                {
                    "auto_reply_message": "Auto-reply message is required when auto-reply is enabled."
                }
            )

        return data


class FontSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserSettings
        fields = ["font_size", "font_family"]


class AttachmentSerializer(serializers.ModelSerializer):
    file_url = serializers.SerializerMethodField()
    file_preview = serializers.SerializerMethodField()

    class Meta:
        model = Attachment
        fields = ["id", "file", "filename", "content_type", "file_url", "file_preview"]

    def get_file_url(self, obj):
        request = self.context.get("request")
        if request:
            return request.build_absolute_uri(obj.file.url)
        return None

    def get_file_preview(self, obj):
        # Implement preview logic for supported file types
        supported_preview_types = [
            "image/jpeg",
            "image/png",
            "image/gif",
            "application/pdf",
            "text/plain",
        ]
        if obj.content_type in supported_preview_types:
            # Generate or return preview URL/data
            return f"/preview/{obj.id}"
        return None


class UserSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserSettings
        fields = [
            "notifications_enabled",
            "font_size",
            "font_family",
            "dark_mode",
            "auto_reply_enabled",
            "auto_reply_message",
            "signature",
            "auto_reply_from_email",
        ]


class LabelSerializer(serializers.ModelSerializer):
    class Meta:
        model = Label
        fields = ["id", "user", "name", "color", "emails"]


class EmailSerializer(serializers.ModelSerializer):
    sender = serializers.SlugRelatedField(slug_field="email", read_only=True)
    sender_id = serializers.SerializerMethodField()
    sender_profile_url = serializers.SerializerMethodField()
    recipients = serializers.SlugRelatedField(
        slug_field="email", many=True, read_only=True
    )
    cc = serializers.SlugRelatedField(slug_field="email", many=True, read_only=True)
    bcc = serializers.SlugRelatedField(slug_field="email", many=True, read_only=True)

    # Modify the attachments serialization
    attachments = serializers.SerializerMethodField()

    labels = LabelSerializer(many=True, read_only=True)
    is_reply = serializers.SerializerMethodField()

    class Meta:
        model = Email
        fields = [
            "id",
            "sender",
            "sender_id",
            "sender_profile_url",
            "recipients",
            "cc",
            "bcc",
            "subject",
            "body",
            "attachments",
            "sent_at",
            "is_read",
            "is_starred",
            "is_draft",
            "is_trashed",
            "reply_to",
            "headers",
            "labels",
            "is_reply",
        ]

    def get_attachments(self, obj):
        attachments = obj.attachments.all()
        serialized = AttachmentSerializer(
            attachments, many=True, context=self.context
        ).data
        return serialized

    def get_is_reply(self, obj):
        return obj.reply_to is not None

    def get_sender_id(self, obj):
        return obj.sender.id

    def get_sender_profile_url(self, obj):
        sender_profile = UserProfile.objects.filter(user=obj.sender).first()
        return (
            sender_profile.profile_picture.url
            if sender_profile and sender_profile.profile_picture
            # else None
            else "https://storage.googleapis.com/gottenmail/dog.png"
        )


class CreateEmailSerializer(serializers.ModelSerializer):
    recipients = serializers.JSONField(write_only=True)
    cc = serializers.JSONField(write_only=True, required=False, allow_null=True)
    bcc = serializers.JSONField(write_only=True, required=False, allow_null=True)
    attachments = serializers.ListField(
        child=serializers.FileField(required=False), required=False
    )

    class Meta:
        model = Email
        fields = [
            "recipients",
            "cc",
            "bcc",
            "subject",
            "body",
            "attachments",
            "is_draft",
            "reply_to",
        ]

    def validate(self, attrs):
        # Ensure recipients are valid email addresses
        recipients = attrs.get("recipients", [])
        if not isinstance(recipients, list):
            try:
                # Try parsing if it's a JSON string
                recipients = json.loads(recipients)
            except (TypeError, json.JSONDecodeError):
                raise serializers.ValidationError("Invalid recipients format")

        attrs["recipients"] = recipients

        # Optional: Validate CC and BCC similarly
        if "cc" in attrs and attrs["cc"]:
            cc = attrs["cc"]
            if not isinstance(cc, list):
                try:
                    cc = json.loads(cc)
                except (TypeError, json.JSONDecodeError):
                    raise serializers.ValidationError("Invalid CC format")
            attrs["cc"] = cc

        if "bcc" in attrs and attrs["bcc"]:
            bcc = attrs["bcc"]
            if not isinstance(bcc, list):
                try:
                    bcc = json.loads(bcc)
                except (TypeError, json.JSONDecodeError):
                    raise serializers.ValidationError("Invalid BCC format")
            attrs["bcc"] = bcc

        return attrs

    def create(self, validated_data):
        # Extract related data
        recipients_emails = validated_data.pop("recipients", [])
        cc_emails = validated_data.pop("cc", [])
        bcc_emails = validated_data.pop("bcc", [])
        attachments = validated_data.pop("attachments", [])

        # Get the currently authenticated user as the sender
        sender = self.context["request"].user

        # Find or create users for recipients
        print("doing recipients")
        recipients = []
        for email in recipients_emails:
            user, created = User.objects.get_or_create(email=email)
            print(user)
            recipients.append(user)

        cc = []
        if cc_emails:
            for email in cc_emails:
                user, created = User.objects.get_or_create(email=email)
                cc.append(user)

        bcc = []
        if bcc_emails:
            for email in bcc_emails:
                user, created = User.objects.get_or_create(email=email)
                bcc.append(user)

        # Validate recipients
        if not recipients:
            raise serializers.ValidationError(
                {"recipients": "At least one recipient is required."}
            )

        attachment_objects = []
        if attachments:
            for attachment_data in attachments:
                try:
                    print("Processing attachment:", attachment_data)
                    print("Attachment name:", attachment_data.name)
                    print("Attachment content type:", attachment_data.content_type)

                    attachment = Attachment.objects.create(
                        file=attachment_data,
                        filename=attachment_data.name,
                        content_type=attachment_data.content_type,
                    )
                    attachment_objects.append(attachment)
                except Exception as e:
                    print(f"Error creating attachment: {e}")

        email = Email.objects.create(sender=sender, **validated_data)
        # Set recipients, CC, and BCC
        email.recipients.set(recipients)
        email.cc.set(cc)
        email.bcc.set(bcc)
        # Add attachments
        email.attachments.add(*attachment_objects)

        # Notify recipients only after everything is set
        notify_recipients(email)

        return email


def notify_recipients(email):
    recipients = set(email.recipients.all())
    recipients.update(email.cc.all())
    recipients.update(email.bcc.all())

    if not recipients:
        print("No recipients to notify")
        return
    
    print(recipients)

    email_data = EmailSerializer(email).data
    channel_layer = get_channel_layer()

    for recipient in recipients:
        try:
            notification = Notification.objects.create(
                user=recipient,
                message=f"You have a new email from {email.sender.first_name} {email.sender.last_name}!",
                related_email=email,
                notification_type="email",
            )
            notification_data = NotificationSerializer(notification).data
            message = {
                "type": "email_notification",
                "email": email_data,
                "notification": notification_data,
            }
            group = f"user_{recipient.id}_emails"
            async_to_sync(channel_layer.group_send)(group, message)

            handle_auto_reply(email, recipient)
        except Exception as e:
            print(f"Error notifying user {recipient.id}: {e}")


def handle_auto_reply(email: Email, recipient):
    print("handling auto reply")
    try:
        if not email.is_auto_replied:
            user_settings = UserSettings.objects.get(user=recipient)
            print("Found user")
            if user_settings.auto_reply_enabled:
                auto_reply_message = user_settings.auto_reply_message
                auto_reply_email = Email.objects.create(
                    sender=recipient,
                    subject=f"Re: {email.subject}",
                    body=plain_text_to_quill_delta(auto_reply_message),
                    sent_at=timezone.now(),
                    is_auto_replied=True,
                    reply_to=email,
                )
                # Set recipients using the set() method
                auto_reply_email.recipients.set([email.sender])
                auto_reply_email.save()  # Ensure the email is saved

                # Serialize auto-reply email data
                auto_reply_email_data = EmailSerializer(auto_reply_email).data

                # Create Notification object for auto-reply
                auto_reply_notification = Notification.objects.create(
                    user=email.sender,
                    message=f"You have received an auto-reply from {recipient.first_name} {recipient.last_name}.",
                    related_email=auto_reply_email,
                    notification_type="email",
                )

                # Serialize auto-reply notification data
                auto_reply_notification_data = NotificationSerializer(
                    auto_reply_notification
                ).data

                # Combine auto-reply email and notification data
                auto_reply_message = {
                    "type": "email_notification",
                    "email": auto_reply_email_data,
                    "notification": auto_reply_notification_data,
                }

                print()
                print()

                print(auto_reply_notification_data)

                group = f"user_{email.sender.id}_emails"
                print(f"Sending auto-reply to group: {group}")
                async_to_sync(get_channel_layer().group_send)(group, auto_reply_message)
    except UserSettings.DoesNotExist:
        print(f"No user settings found for user {recipient.id}")
    except Exception as e:
        print(f"Error handling auto-reply for user {recipient.id}: {e}")


def plain_text_to_quill_delta(text):
    # Convert plain text to Quill Delta format
    delta = f'[{{"insert": "{text}\\n"}}]'
    return delta


class EmailDetailSerializer(
    EmailSerializer
):  # Inherit for detail view, adds reply info
    replies = serializers.SerializerMethodField()

    class Meta:
        model = Email
        fields = "__all__"  # or list specific fields, including 'replies'

    def get_replies(self, obj):
        # Serialize replies, possibly with a simplified serializer
        return EmailSerializer(obj.replies.all(), many=True, context=self.context).data


class OtherUserProfileSerializer(serializers.ModelSerializer):
    first_name = serializers.CharField(source="user.first_name")
    last_name = serializers.CharField(source="user.last_name")
    birthdate = serializers.DateField(format="%Y-%m-%d")

    class Meta:
        model = UserProfile
        fields = ["first_name", "last_name", "birthdate", "bio"]


class SimplifiedEmailSerializer(serializers.ModelSerializer):
    class Meta:
        model = Email
        fields = ["id"]


class NotificationSerializer(serializers.ModelSerializer):
    related_email = SimplifiedEmailSerializer(read_only=True)

    class Meta:
        model = Notification
        fields = [
            "id",
            "message",
            "is_read",
            "created_at",
            "notification_type",
            "related_email",
        ]
        read_only_fields = [
            "message",
            "created_at",
            "notification_type",
            "related_email",
        ]


class PhoneNumberSerializer(serializers.Serializer):
    phone_number = serializers.CharField(max_length=20)


class VerificationCodeSerializer(serializers.Serializer):
    phone_number = serializers.CharField(max_length=20)
    code = serializers.CharField(max_length=6)


class PasswordResetSerializer(serializers.Serializer):
    email = serializers.EmailField()


class Enable2FASerializer(serializers.Serializer):
    pass


class PasswordResetConfirmSerializer(serializers.Serializer):
    email = serializers.EmailField()
    code = serializers.CharField()
    new_password = serializers.CharField(write_only=True)


class ForgetPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField()
    phone_number = serializers.CharField(max_length=20)
