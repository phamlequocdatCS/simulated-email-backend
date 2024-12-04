from twilio.rest import Client
from GotMail.super_secrets import (
    TWILIO_ACCOUNT_SID,
    TWILIO_AUTH_TOKEN,
    TWILIO_VERIFY_SERVICE_SID,
)


def send_verification_code(phone_number):
    print(f"received {phone_number}")
    client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
    verification = client.verify.v2.services(
        TWILIO_VERIFY_SERVICE_SID
    ).verifications.create(to=phone_number, channel="sms")
    return verification.sid


def verify_code(user, code):
    client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
    check = client.verify.v2.services(
        TWILIO_VERIFY_SERVICE_SID
    ).verification_checks.create(to=user.phone_number, code=code)
    print(f"User give: {code}")
    if check.status == "approved":
        user.is_phone_verified = True
        user.save()
        return True
    return False
