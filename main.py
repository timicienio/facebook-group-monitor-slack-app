import os
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from pymongo.mongo_client import MongoClient
from dotenv import load_dotenv

load_dotenv()

# Load environment variables
SLACK_BOT_TOKEN = os.environ.get("SLACK_BOT_TOKEN")
SLACK_APP_TOKEN = os.environ.get("SLACK_APP_TOKEN")
MONGO_USERNAME = os.environ.get("MONGO_USERNAME")
MONGO_PASSWORD = os.environ.get("MONGO_PASSWORD")

if not SLACK_BOT_TOKEN or not SLACK_APP_TOKEN:
    raise ValueError("Slack tokens must be set in environment variables.")

# Initialize MongoDB client
uri = f"mongodb+srv://{MONGO_USERNAME}:{MONGO_PASSWORD}@facebook-group-monitor.wjbipuo.mongodb.net/?retryWrites=true&w=majority&appName=facebook-group-monitor"
mongoClient = MongoClient(uri)
db = mongoClient["facebook-group-monitor"]
collection = db["posts"]

# Initialize your app with your bot token
app = App(token=SLACK_BOT_TOKEN)

# Define a function that sends a message to a channel upon connection
def send_welcome_message():
    try:
        # Send a message to a specific channel
        app.client.chat_postMessage(
            channel="#36-資訊-hackathon-test",  # Change to your desired channel
            text="Hello, I am now connected and online!"
        )
    except Exception as e:
        print(f"Error sending welcome message: {e}")

# This will run when the app is mentioned
@app.event("app_mention")
def handle_app_mention(event, say):
    send_welcome_message()

# Function to process MongoDB changes and post to Slack
def process_mongo_changes():
    try:
        with collection.watch() as stream:
            for change in stream:
                operation_type = change["operationType"]
                document_key = change["documentKey"]
                full_document = change.get("fullDocument", {})
                if operation_type == "insert":
                    content = f"{full_document['content']}"
                    author = f"{full_document['author']}"
                    href = f"{full_document['href']}"
                    blocks=[
                        {
                            "type": "header",
                            "text": {
                                "type": "plain_text",
                                "text": "最新貼文"
                            }
                        },
                        {
                            "type":"divider"
                        },
                        {
                            "type": "section",
                            "text": {
                                "type": "mrkdwn",
                                "text": '*貼文摘要*'+'\n'+"摘要完的貼文"
                            }
                        },
                        {
                            "type":"divider"
                        },
                        {
                            "type": "section",
                            "text": {
                                "type": "mrkdwn",
                                "text": '*'+author+'*'+'\n'+content
                            }
                        },
                        {
                            "type":"divider"
                        },
                        {
                            "type": "section",
                            "text": {
                                "type": "mrkdwn",
                                "text":"原始貼文："
                            },
                            "accessory":{
                                "type":"button",
                                "text":{
                                    "type":"plain_text",
                                    "text":"前往"
                                },
                                "value":"open_post_value", 
                                "url": href, 
                                "action_id":"open_post"
                            }
                        }
                    ]
                elif operation_type == "update":
                    message = f"Document updated: {document_key}"
                elif operation_type == "delete":
                    message = f"Document deleted: {document_key}"
                else:
                    message = f"Unhandled operation: {operation_type}"

                try:
                    app.client.chat_postMessage(
                        channel="#36-資訊-hackathon-test",  # Change to your desired channel
                        text="NTU is BOILING--!",
                        blocks=blocks
                    )
                except Exception as e:
                    print(f"Error sending message to Slack: {e}")

    except Exception as e:
        print(f"Error watching MongoDB collection: {e}")

if __name__ == "__main__":
    # Start the MongoDB change stream watcher in a separate thread
    import threading
    watcher_thread = threading.Thread(target=process_mongo_changes)
    watcher_thread.start()

    # Create a SocketModeHandler instance
    handler = SocketModeHandler(app, SLACK_APP_TOKEN)
    # Start the Socket Mode handler
    handler.start()
