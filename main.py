from __future__ import division

import os
import re
import sys

from flask import Flask, render_template

import pyaudio
from six.moves import queue
from google.cloud import pubsub_v1


from flask_socketio import SocketIO

os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "/home/petermbrown064/cloudshell_open/Meeting-skivers-team13/credentials.json"

# Audio recording parameters
RATE = 44100
CHUNK = int(RATE / 10)  # 100ms
app = Flask(__name__)

#buffer = queue.Queue()

app.config['SECRET_KEY'] = 'v019j3h2hk3'
# Cross Origin Resource Sharing
socketio = SocketIO(app, cors_allowed_origins="*")

@socketio.on('connect')
def handle_connection():
    print('I\'m connected server side')

@socketio.on('disconnect')
def test_disconnect():
    print('Client disconnected')

@socketio.on('audio_chunk')
def get_chunk(chunk, trigger_word, teams_webhook):
    print(f"publishing chunk with trigger_word={trigger_word}, teams_webhook={teams_webhook[:5]}...")
    publisher.publish(topic_path, chunk, trigger_word=trigger_word, teams_webhook=teams_webhook)

@socketio.on('settings')
def get_settings(settings):
    print(f"Got settings {settings}")
    trigger_words = settings.get("trigger_words")
    webhook_url = settings.get("webhook_url")

######### PUBSUB SETUP

project_id = "lbghack2021team13"
topic_id = "audio-chunks-topic"

publisher = pubsub_v1.PublisherClient()
topic_path = publisher.topic_path(project_id, topic_id)

######### END OF PUBSUB SETUP


@app.route("/")
def main():
    return render_template("landing_page.html")


if __name__ == "__main__":
    print("starting flask app...")
    socketio.run(app, host="127.0.0.1", port=5000)
