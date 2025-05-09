from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
import os
from dotenv import load_dotenv

load_dotenv()
SLACK_API_KEY = os.getenv("SLACK_API_KEY")
client = WebClient(token=SLACK_API_KEY)

def get_channel_id(channel_name):
    try:
        result = client.conversations_list(types="public_channel", limit=1000)
        for channel in result['channels']:
            if channel['name'] == channel_name:
                return channel['id']
        return None
    except SlackApiError as e:
        print(f"Error fetching channels: {e.response['error']}")
        return None

def create_channel(channel_name):
    try:
        response = client.conversations_create(name=channel_name)
        return response['channel']['id']
    except SlackApiError as e:
        if e.response['error'] == 'name_taken':
            print(f"Channel '{channel_name}' already exists.")
        else:
            print(f"Error creating channel: {e.response['error']}")
        return None

def send_message(channel_id, message):
    try:
        response = client.chat_postMessage(channel=channel_id, text=message)
        print(f"Message sent: {response['ts']}")
    except SlackApiError as e:
        print(f"Error sending message: {e.response['error']}")

def send_pdf(channel_id, file_path, message=""):
    try:
        upload_text_file = client.files_upload_v2(
        channel=channel_id,
        title="Benefits Table",
        file=file_path,
        initial_comment=message,
    )
        print("PDF uploaded successfully.")
    except SlackApiError as e:
        print(f"Error uploading file: {e.response['error']}")

if __name__ == "__main__":
    channel_name = "quote-notifications"
    message = "Hello from Python Slack Bot! Here's your file."
    pdf_file_path = "Benefits Table.pdf"

    channel_id = get_channel_id(channel_name)
    if not channel_id:
        print(f"Channel '{channel_name}' not found. Creating...")
        channel_id = create_channel(channel_name)

    if channel_id:
        # send_message(channel_id, message)
        send_pdf(channel_id, pdf_file_path, message)
