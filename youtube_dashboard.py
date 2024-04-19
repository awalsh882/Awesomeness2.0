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
        # Create a request to get subscriptions with expanded parts
        subscription_request = youtube.subscriptions().list(
            part='snippet,contentDetails,id,subscriberSnippet',  # Including more parts
            channelId=channel_id,
            maxResults=50,  # Maximum allowed by API
            pageToken=next_page_token
        )
        response = subscription_request.execute()

        # Collect all subscriptions and additional data
        for item in response.get('items', []):
            subscription = {
                'id': item.get('id'),
                'title': item['snippet']['title'],
                'description': item['snippet']['description'],
                'thumbnail_url': item['snippet']['thumbnails']['default']['url'],
                'content_details': item.get('contentDetails'),
                'subscriber_details': item.get('subscriberSnippet')
            }
            all_subscriptions.append(subscription)

        # Check if there is a next page
        next_page_token = response.get('nextPageToken')
        if not next_page_token:
            break

    return all_subscriptions


@app.route('/GET/<channel_id>')
def home(channel_id):
    subscriptions = fetch_subscriptions(channel_id)
    subscription_info = []

    for subscription in subscriptions:
        channel_title = subscription['snippet']['title']
        subscribed_channel_id = subscription['snippet']['resourceId']['channelId']
        subscription_info.append({
            "title": channel_title,
            "channel_id": subscribed_channel_id
        })

    return jsonify(subscription_info)

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=80)
