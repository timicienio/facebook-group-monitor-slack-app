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
    template="Please summarize the following text and output in CH-TW:\n\n{text}\n\nSummary:",
)
summarization_chain = LLMChain(llm=llm, prompt=summarization_prompt)


def summarize_text(text):
    summary = summarization_chain.run(text=text)
    return summary


# Define a function that sends a message to a channel upon connection
def send_welcome_message():
    try:
        # Send a message to a specific channel
        app.client.chat_postMessage(
            channel="#36-資訊-hackathon-test",  # Change to your desired channel
            text="Hello, I am now connected and online!",
        )
    except Exception as e:
        print(f"Error sending welcome message: {e}")


# This will run when the app is mentioned
@app.event("app_mention")
def handle_app_mention(event, say):
    send_welcome_message()


def process_mongo_changes():
    try:
        with collection.watch() as stream:
            for change in stream:
                operation_type = change["operationType"]
                full_document = change.get("fullDocument", {})
                if operation_type == "insert":
                    content = f"{full_document['content']}"
                    author = f"{full_document['author']}"
                    href = f"{full_document['href']}"

                    # Check content length for summary
                    if len(content) > 150:
                        input_text = content
                        summary = summarize_text(input_text)
                        summary_section = {
                            "type": "section",
                            "text": {
                                "type": "mrkdwn",
                                "text": "*貼文摘要*" + "\n" + summary + "\n",
                            },
                        }
                    else:
                        summary_section = None

                    blocks = [
                        {
                            "type": "header",
                            "text": {
                                "type": "plain_text",
                                "text": ":bookmark_tabs: 最新貼文",
                            },
                        },
                    ]

                    if summary_section:
                        blocks.append(summary_section)

                    blocks.extend(
                        [
                            {"type": "divider"},
                            {
                                "type": "section",
                                "text": {
                                    "type": "mrkdwn",
                                    "text": "*" + author + "*" + "\n" + content,
                                },
                            },
                            # {"type": "divider"},
                            {
                                "type": "section",
                                "text": {
                                    "type": "mrkdwn",
                                    "text": f"_原始貼文連結:_{href}",
                                },
                            },
                        ]
                    )

                    try:
                        app.client.chat_postMessage(
                            channel="#36-資訊-hackathon-test",  # Change to your desired channel
                            text=f"New post from {author} is boiling",
                            blocks=blocks,
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
