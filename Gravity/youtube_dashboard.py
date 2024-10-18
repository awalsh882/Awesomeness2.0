import os
from googleapiclient.discovery import build
from flask import Flask, request, jsonify

# Initialize Flask
app = Flask(__name__)

# API setup
SCOPES = ['https://www.googleapis.com/auth/youtube.readonly']
API_SERVICE_NAME = 'youtube'
API_VERSION = 'v3'
youtube_api_key = 'AIzaSyCxHaESSOAzE-4UWLBlfMuLi_BeeamKyWc'

# Initialize YouTube API client
youtube = build(API_SERVICE_NAME, API_VERSION, developerKey=youtube_api_key)

def fetch_subscriptions(channel_id):
    all_subscriptions = []
    next_page_token = None

    while True:
        subscription_request = youtube.subscriptions().list(
            part='snippet,contentDetails,id,subscriberSnippet',
            channelId=channel_id,
            maxResults=50,
            pageToken=next_page_token
        )
        response = subscription_request.execute()

        for item in response.get('items', []):
            snippet = item.get('snippet', {})
            subscription = {
                'id': item.get('id'),
                'title': snippet.get('title', 'No title available'),
                'description': snippet.get('description', 'No description available')
            }
            all_subscriptions.append(subscription)

        next_page_token = response.get('nextPageToken')
        if not next_page_token:
            break

    return all_subscriptions

@app.route('/GET/<channel_id>')
def home(channel_id):
    try:
        subscriptions = fetch_subscriptions(channel_id)
        return jsonify(subscriptions)  # Directly return all subscription info
    except Exception as e:
        app.logger.error(f"Failed to fetch subscriptions: {e}")
        return jsonify({"error": "Failed to process request"}), 500

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=80)
