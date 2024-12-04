import uuid

from django.contrib.auth.models import (
    AbstractUser,
    BaseUserManager,
)
from django.core.validators import RegexValidator
from django.db import models
from django.utils import timezone
from pydantic import ValidationError


class CustomUserManager(BaseUserManager):
    def create_user(self, phone_number, password=None, **extra_fields):
        if not phone_number:
            raise ValueError("The Phone Number field must be set")
        user = self.model(phone_number=phone_number, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, phone_number, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)

        return self.create_user(phone_number, password, **extra_fields)


phone_regex = RegexValidator(
    regex=r"^\+?1?\d{9,15}$",
    message="Phone number must be entered in the format: '+999999999'. Up to 15 digits allowed.",
)


class User(AbstractUser):
    phone_number = models.CharField(
        validators=[phone_regex], max_length=20, unique=True
    )
    # Add verification status for two-step verification
    is_phone_verified = models.BooleanField(default=False)

    # Session token for persistent login
    session_token = models.CharField(max_length=255, blank=True, null=True)
    session_expiry = models.DateTimeField(blank=True, null=True)

    username = models.CharField(
        max_length=150, unique=True, blank=True, null=True
    )  # For admin, if needed

    password_reset_token = models.CharField(max_length=255, blank=True, null=True)
    password_reset_expires = models.DateTimeField(blank=True, null=True)

    verification_code = models.CharField(max_length=6, blank=True, null=True)
    verification_code_expires = models.DateTimeField(blank=True, null=True)

    # Use phone number as username field
    USERNAME_FIELD = "phone_number"
    REQUIRED_FIELDS = ["first_name", "last_name"]

    # Set the custom manager
    objects = CustomUserManager()

    groups = models.ManyToManyField(
        "auth.Group",
        related_name="gotmail_user_set",  # Unique related name
        blank=True,
    )
    user_permissions = models.ManyToManyField(
        "auth.Permission",
        related_name="gotmail_user_set",  # Unique related name
        blank=True,
    )

    def generate_password_reset_token(self):
        self.password_reset_token = str(uuid.uuid4())
        self.password_reset_expires = timezone.now() + timezone.timedelta(hours=1)
        self.save()

    def generate_verification_code(self):
        self.verification_code = str(uuid.uuid4())[:6]
        self.verification_code_expires = timezone.now() + timezone.timedelta(minutes=10)
        self.save()

    def __str__(self):
        return self.phone_number

    def generate_session_token(self):
        """
        Generate a unique session token.

        Returns:
            str: A unique UUID-based session token
        """
        print("Generating session token")
        self.session_token = str(uuid.uuid4())
        self.session_expiry = timezone.now() + timezone.timedelta(days=30)
        self.save()


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    profile_picture = models.ImageField(
        upload_to="profile_pictures/", blank=True, null=True
    )
    bio = models.TextField(blank=True)  # Add a bio field
    birthdate = models.DateField(blank=True, null=True)  # Add birthdate field
    two_factor_enabled = models.BooleanField(default=False)


class Email(models.Model):
    message_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    sender = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="emails_sent"
    )
    recipients = models.ManyToManyField(
        User, related_name="emails_received", blank=True
    )
    cc = models.ManyToManyField(User, related_name="emails_cc", blank=True)
    bcc = models.ManyToManyField(User, related_name="emails_bcc", blank=True)
    subject = models.CharField(max_length=255)
    body = models.TextField()  # Or RichTextField if using a rich text editor
    attachments = models.ManyToManyField("Attachment", blank=True)
    sent_at = models.DateTimeField(default=timezone.now)
    is_read = models.BooleanField(default=False)  # Mark as read/unread
    is_starred = models.BooleanField(default=False)  # Starred emails
    is_draft = models.BooleanField(default=False)  # Drafts
    is_trashed = models.BooleanField(default=False)  # Trashed emails
    is_auto_replied = models.BooleanField(default=False)  # Auto-reply email

    reply_to = models.ForeignKey(
        "self", on_delete=models.SET_NULL, null=True, blank=True, related_name="replies"
    )
    headers = models.JSONField(blank=True, null=True)  # Stores metadata like message-id

    def __str__(self):
        return f"Email from {self.sender} to {self.recipients.all()} - {self.subject}"

    def can_view(self, user):
        return (
            self.sender == user
            or user in self.recipients.all()
            or user in self.cc.all()
            or user in self.bcc.all()
        )


class Attachment(models.Model):
    def validate_file_size(value):
        filesize = value.size

        if filesize > 10 * 1024 * 1024:  # 10MB limit
            raise ValidationError("The maximum file size that can be uploaded is 10MB")

    file = models.FileField(upload_to="attachments/", validators=[validate_file_size])
    filename = models.CharField(max_length=255)
    content_type = models.CharField(max_length=255, null=True, blank=True)

    def __str__(self):
        return self.filename


class Label(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="labels")
    name = models.CharField(max_length=50)
    # Add a color field for visual organization (optional):
    color = models.CharField(
        max_length=7, default="#808080", blank=True
    )  # Hex color code
    emails = models.ManyToManyField(Email, related_name="labels", blank=True)

    def __str__(self):
        return self.name

    class Meta:
        unique_together = ("user", "name")  # Ensure unique label names per user


class UserSettings(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="settings")
    notifications_enabled = models.BooleanField(default=True)
    # Use choices for font size and family for a predefined list (optional):
    FONT_SIZES = [(12, "Small"), (14, "Medium"), (16, "Large")]  # Example sizes
    FONT_FAMILIES = [
        ("sans-serif", "Sans-serif"),
        ("serif", "Serif"),
        ("monospace", "Monospace"),
    ]  # Example
    font_size = models.IntegerField(choices=FONT_SIZES, default=14)
    font_family = models.CharField(
        max_length=50, choices=FONT_FAMILIES, default="sans-serif"
    )

    dark_mode = models.BooleanField(default=False)
    auto_reply_enabled = models.BooleanField(default=False)
    auto_reply_message = models.TextField(blank=True, null=True)

    # Auto-reply scheduling
    auto_reply_start_date = models.DateTimeField(blank=True, null=True)
    auto_reply_end_date = models.DateTimeField(blank=True, null=True)

    def __str__(self):
        return f"Settings for {self.user.phone_number}"

    def toggle_dark_mode(self):
        self.dark_mode = not self.dark_mode
        self.save()

    def enable_auto_reply(self):
        self.auto_reply_enabled = True
        self.save()

    def disable_auto_reply(self):
        self.auto_reply_enabled = False
        self.save()


class Notification(models.Model):
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="notifications"
    )
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    notification_type = models.CharField(
        max_length=50,
        choices=[
            ("email", "Email"),
            ("system", "System"),
        ],
    )
    related_email = models.ForeignKey(
        Email, on_delete=models.SET_NULL, null=True, blank=True
    )

    class Meta:
        ordering = ["-created_at"]
