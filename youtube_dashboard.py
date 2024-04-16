
import flask

import os
from googleapiclient.discovery import build
from flask import Flask, request, jsonify

# Initialize Flask
app = flask.Flask(__name__)

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
        # Create a request to get subscriptions
        request = youtube.subscriptions().list(
            part='snippet',
            channelId=channel_id,
            maxResults=50,  # Maximum allowed by API
            pageToken=next_page_token
        )
        response = request.execute()

        # Collect all subscriptions
        all_subscriptions.extend(response.get('items', []))

        # Check if there is a next page
        next_page_token = response.get('nextPageToken')
        if not next_page_token:
            break

    return all_subscriptions

@app.route('/GET/<channel_id>')
def home(channel_id):
    #channel_id = 'UCDE-xKodQrgV6SFoirM-u2Q'  
    subscriptions = fetch_subscriptions(channel_id)
    subscription_info = []

    for subscription in subscriptions:
        channel_title = subscription['snippet']['title']
        subscribed_channel_id = subscription['snippet']['resourceId']['channelId']
        subscription_info.append(f"Subscribed Channel Title: {channel_title}, Channel ID: {subscribed_channel_id}")

    return jsonify(subscription_info)

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=80)
