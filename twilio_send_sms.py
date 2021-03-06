from twilio.rest import TwilioRestClient
import os

TWILIO_ACCOUNT_SID = os.environ['TWILIO_ACCOUNT_SID']
TWILIO_AUTH_TOKEN = os.environ['TWILIO_AUTH_TOKEN']
TWILIO_NUMBER = os.environ['TWILIO_NUMBER']

client = TwilioRestClient(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)


def send_text(to_number, message):
    # takes a telephone number and a message
    # sends a message from twilio number

    to_number = to_number
    body_message = message

    message = client.messages.create(from_=TWILIO_NUMBER,
                                     to=to_number,
                                     body=body_message)

    print message.sid
