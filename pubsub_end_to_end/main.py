import base64
from google.cloud import speech
import json
from string import punctuation
import spacy
import os
import datetime
import requests
import redis

redis_host = '10.162.125.211'
redis_port = 6379
redis_client = redis.StrictRedis(host=redis_host, port=redis_port)


os.environ["SENTENCES_BEFORE"] = "2"
os.environ["SENTENCES_AFTER"] = "2"


def hello_pubsub(event, context):
    """Triggered from a message on a Cloud Pub/Sub topic.
    Args:
         event (dict): Event payload.
         context (google.cloud.functions.Context): Metadata for the event.
    """
    audio_chunk = base64.b64decode(event['data'])

    trigger_word = event['attributes']['trigger_word']
    teams_webhook = event['attributes']['teams_webhook']
    print(f"Trigger word: {trigger_word}, Teams webhook: {teams_webhook}")
    transcription = transcribe(audio_chunk)
    print(f"Transcription: {transcription}")
    if transcription:
        print(f'adding to redis: {transcription}')
        redis_client.rpush('previous_transcripts', transcription)

    processed_transcripts = process_transcript(transcription, trigger_word)
    print(f"Processed transcript: {processed_transcripts}")

    if processed_transcripts:
        previous_transcripts = []
        while(redis_client.llen('previous_transcripts')!=0):
            prev_transcript = redis_client.lpop('previous_transcripts').decode("utf-8")
            print(f'Got from redis: {prev_transcript}')
            previous_transcripts.append(prev_transcript)

        for processed_output in processed_transcripts:
            if previous_transcripts:
                message_body = ' '.join(previous_transcripts) + ' ' + processed_output['message_body']
            else:
                message_body = processed_output['message_body']
            print(f'Message body = {message_body}')
            run_publish_message(
                processed_output['title'],
                message_body,
                teams_webhook
            )


def transcribe(audio_chunk):

    client = speech.SpeechClient()

    audio = speech.RecognitionAudio(content=audio_chunk)

    config = speech.RecognitionConfig(
        encoding=speech.RecognitionConfig.AudioEncoding.ENCODING_UNSPECIFIED,
        language_code="en-GB",
        audio_channel_count=1,
        enable_automatic_punctuation=True,
    )

    response = client.recognize(config=config, audio=audio)

    transcript = []
    for res in response.results:
        for alt in res.alternatives:
            transcript.append(alt.transcript)

    transcript = ' '.join(transcript)

    return transcript


def get_sentences_from_transcript(transcript):
    # Load spacy model package "en_core_web_sm"
    nlp = spacy.load('en_core_web_sm')
    
    # Read sentences as strings into list
    about_transcript = nlp(transcript)
    sentences = [sent.text for sent in about_transcript.sents]
    
    return sentences


def get_sentences(transcript, keyword: str, ind_before: int, ind_after: int):
    
    transcript_list = get_sentences_from_transcript(transcript)
    
    # Return list of indices containing name parameter
    indices = [i for i, s in enumerate(transcript_list) if keyword.lower() in s.lower()]
    
    sentences = []
    
    for ind in indices:
        min_ind = ind - ind_before
        max_ind = ind + ind_after
        sentences.append(transcript_list[min_ind:max_ind])

    return sentences


def create_title(processed_transcript: str, keyword: str):
    """Creates a relevant title for the alert depending on whether a question was asked to the user."""
    if '?' in ''.join(processed_transcript):
        return f'{keyword}, you have been asked a question'
    else:
        return f'{keyword}, your name has been mentioned'
    
    
def process_transcript(transcript, keyword):
    
    # Set up parameters
    SENTENCES_BEFORE = int(os.environ.get('SENTENCES_BEFORE'))
    SENTENCES_AFTER = int(os.environ.get('SENTENCES_AFTER'))
    
    print('Starting Process Transcript...')
    
    # Process data
    processed_transcript_list = get_sentences(transcript, keyword, SENTENCES_BEFORE, SENTENCES_AFTER) 

    if len(processed_transcript_list) > 0:
        outputs = []
        for transcript_number, processed_transcript in enumerate(processed_transcript_list):
            title = create_title(processed_transcript, keyword)
            json_output = {'title': title, 'message_body': ' '.join(processed_transcript)}
            outputs.append(json_output)
        return outputs
    else:
        print('No instance of keyword found.')


def publish_message(meeting_dict:dict, automated_responses:list, notification_url:str):
    """
    Args:
        meeting_dict: Dictionary of values and information from the meeting
        automated_response: Generic responses to choose from
        notification_url: Webhook url to notification channel
    """
    

    payload = {
    "@type": "MessageCard",
    "@context": "http://schema.org/extensions",
    "themeColor": "0076D7",
    "summary": f"{meeting_dict['question_summary']}",
    "sections": [{
        "activityTitle": meeting_dict['message_title'],
        "activityImage": "https://i.pcmag.com/imagery/reviews/05Jidi9HqQuegaS1lFvCADR-19.fit_scale.size_1028x578.v_1569892613.jpg",
        "facts": [{
            "name": "Received",
            "value": datetime.datetime.now().strftime("%m/%d/%Y, %H:%M:%S")
        }, {
            "name": "Summary",
            "value": meeting_dict['question_summary']
        }],
        "markdown": "false"
    }],
    "potentialAction": [{
        "@type": "OpenUri",
        "name": "Play on mute response",
        "targets": [{
            "os": "default",
            "uri": automated_responses['on_mute']
        }]
    }, {
        "@type": "OpenUri",
        "name": "Play weekend response",
        "targets": [{
            "os": "default",
            "uri":  automated_responses['weekend']
        }]
    }
    ]
    }

    headers = {
        'Content-Type': "application/vnd.microsoft.card.adaptive" 
    }
    
    response = requests.post(notification_url, headers=headers, data=json.dumps(payload))
    print(response.text.encode('utf8'))

def run_publish_message(title, message, webhook_url):
    recording_bucket = "https://storage.googleapis.com/meeting-recorded-replies-team13"
    recording_files = "On%20Mute.m4a,Weekend.m4a".split(',')

    # Define responses
    automated_responses = {
        'on_mute': os.path.join(recording_bucket,recording_files[0]),
        'weekend': os.path.join(recording_bucket,recording_files[1])
    }

    # Get transcript
    meeting_dict = {
        'message_title' : title,
        'question_summary' : message
    }

    publish_message(meeting_dict, automated_responses, webhook_url)
