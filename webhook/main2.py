import requests
import json
import datetime
import os
from google.cloud import storage
from webhook.signedurl import generate_signed_url

def load_file_from_gcs(storage_client, src_bucket_name, src_filename):
    
    bucket = storage_client.get_bucket(src_bucket_name)
    blob = bucket.blob(src_filename)
    
    # Download the contents of the blob as a bytes object
    data = blob.download_as_string(client=None)
    
    print(f'Loaded {src_filename} from {src_bucket_name}')
    transcript = json.loads(data.decode('utf-8'))
    return transcript['title'], '\n'.join(transcript['message_body']), transcript['file']

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
    "summary": f"{meeting_dict['name']}-{meeting_dict['question_summary']}",
    "sections": [{
        "activityTitle": meeting_dict['message_title'],
        "activitySubtitle": meeting_dict['name'],
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
        "name": "See full meeting transcription",
        "targets": [{
            "os": "default",
            "uri": meeting_dict['full_summary_url']
        }]
    },  {
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
    json.dumps(payload)
    headers = {
        'Content-Type': "application/vnd.microsoft.card.adaptive" 
    }
    
    response = requests.post(notification_url, headers=headers, data=json.dumps(payload))
    print(response.text.encode('utf8'))

def run_publish_message(data, context= None):
    # Instantiate a Google Cloud Storage client and specify required bucket and file
    storage_client = storage.Client()

    # Parameters
    SRC_BUCKET_NAME = data['bucket']
    FILE = data['name']
    webhook_url = os.environ.get("DST_CHANNEL_URL")
    recording_bucket = os.environ.get("RECORDING_BUCKET")
    recording_files = os.environ.get("RECORDING_FILES").split(',')
    transcript_bucket = os.environ.get("TRANSCRIPT_BUCKET")


    # Define responses
    automated_responses = {
        'on_mute': os.path.join(recording_bucket,recording_files[0]),
        'weekend': os.path.join(recording_bucket,recording_files[1])
    }

    # Get transcript
    title, message, transcript_file = load_file_from_gcs(storage_client,SRC_BUCKET_NAME,FILE)

    # Generate signed url for full transcript
    signed_url = generate_signed_url(
        service_account_file="/home/cindy_lam_213213/cloudshell_open/Meeting-skivers-team13/sa-file.json",
        http_method="GET",
        bucket_name=transcript_bucket,
        object_name=transcript_file
    )

    # Publish message
    meeting_dict = {
        'name' : FILE[10:].replace('.json','').replace('.txt',''),
        'full_summary_url' : signed_url,#f"https://storage.cloud.google.com/{transcript_bucket}/{transcript_file}?authuser=2",
        'message_title' : title,
        'question_summary' : message
    }

    publish_message(meeting_dict, automated_responses, webhook_url)


def main():
    gcs_test_object = {
        "name": "PROCESSED_multiple_speakers_punctuation_v4_6.json",
        "bucket": "meeting-transcript-processed-team13"
    }
    
    os.environ["TRANSCRIPT_BUCKET"] = "meeting-transcript-team13"
    os.environ["RECORDING_BUCKET"] = "https://storage.googleapis.com/meeting-recorded-replies-team13"
    os.environ["RECORDING_FILES"] = "On%20Mute.m4a,Weekend.m4a"
    os.environ["DST_CHANNEL_URL"] = "https://cdogcphack.webhook.office.com/webhookb2/1ca2b102-091b-4bc0-a87d-e06d05b73026@41507c88-8a7f-4979-ac87-7a4d61127d74/IncomingWebhook/868e683ac5f4466daeedf549983fe6d3/09e51fdb-7b95-4d1d-9646-b907cffc8ee4"

    run_publish_message(gcs_test_object)

if __name__ == "__main__":
    
    main()