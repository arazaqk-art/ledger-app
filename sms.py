import os

def send_sms(phone: str, message: str) -> None:
    try:
        from twilio.rest import Client
    except Exception as e:
        print("Twilio import error:", e)
        return

    sid = os.getenv("TWILIO_SID")
    token = os.getenv("TWILIO_TOKEN")
    from_no = os.getenv("TWILIO_NUMBER")

    if not sid or not token or not from_no:
        print("Twilio ENV missing")
        return

    try:
        client = Client(sid, token)
        client.messages.create(body=message, from_=from_no, to=phone)
        print("SMS Sent")
    except Exception as e:
        print("Twilio send error:", e)