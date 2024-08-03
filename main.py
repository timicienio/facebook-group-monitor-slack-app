import os
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from pymongo.mongo_client import MongoClient
from dotenv import load_dotenv
from langchain_community.llms import OpenAI
from langchain.chains import LLMChain
from langchain_core.prompts import PromptTemplate

load_dotenv()

# Load environment variables
SLACK_BOT_TOKEN = os.environ.get("SLACK_BOT_TOKEN")
SLACK_APP_TOKEN = os.environ.get("SLACK_APP_TOKEN")
MONGO_USERNAME = os.environ.get("MONGO_USERNAME")
MONGO_PASSWORD = os.environ.get("MONGO_PASSWORD")

# Initialize OpenAI API
llm = OpenAI(temperature=0.7)

if not SLACK_BOT_TOKEN or not SLACK_APP_TOKEN:
    raise ValueError("Slack tokens must be set in environment variables.")

# Initialize MongoDB client
uri = f"mongodb+srv://{MONGO_USERNAME}:{MONGO_PASSWORD}@facebook-group-monitor.wjbipuo.mongodb.net/?retryWrites=true&w=majority&appName=facebook-group-monitor"
mongoClient = MongoClient(uri)
db = mongoClient["facebook-group-monitor"]
collection = db["posts"]

# Initialize your app with your bot token
app = App(token=SLACK_BOT_TOKEN)

summarization_prompt = PromptTemplate(
    input_variables=["text"],
    template="Please summarize the following text and output in CH-TW:\n\n{text}\n\nSummary:"
)
summarization_chain = LLMChain(
    llm=llm,
    prompt=summarization_prompt
)
def summarize_text(text):
    summary = summarization_chain.run(text=text)
    return summary

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
                    input_text = content
                    summary = summarize_text(input_text)
                    blocks=[
                        {
                            "type":"divider"
                        },
                        {
                            "type": "header",
                            "text": {
                                "type": "plain_text",
                                "text": ":bookmark_tabs: 最新貼文"
                            }
                        },
                        {
                            "type":"divider"
                        },
                        {
                            "type": "section",
                            "text": {
                                "type": "mrkdwn",
                                "text": '*貼文摘要*'+'\n'+summary+'\n'
                            }
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
                                "text": f"原始貼文連結：{href}"
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
                        text="Alert! NTU is BOILING",
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
