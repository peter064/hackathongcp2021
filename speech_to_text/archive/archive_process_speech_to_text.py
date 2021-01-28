from google.cloud import speech, storage
import json
import os

DST_BUCKET_NAME = os.environ.get('DST_BUCKET_NAME')


def transcribe_gcs(gcs_uri: str) -> dict:
    """Asynchronously transcribes the audio file specified by the gcs_uri."""

    client = speech.SpeechClient()

    audio = speech.types.RecognitionAudio(uri=gcs_uri)

    config = speech.types.RecognitionConfig(
        encoding=speech.enums.RecognitionConfig.AudioEncoding.FLAC,
        sample_rate_hertz=48000,
        language_code="en-US",
        audio_channel_count=2,
        enable_automatic_punctuation=True,
    )

    operation = client.long_running_recognize(config=config, audio=audio)

    print("Waiting for operation to complete...")

    response = operation.result(timeout=2000)

    transcript = []
    for res in response.results:
        for alt in res.alternatives:
            transcript.append(alt.transcript)

    return transcript

def upload_file_to_gcs(
        src_filename: str,
        transcript: list,
        storage_client,
        DST_BUCKET_NAME: str,
):
    """Uploads a file to Google Cloud Storage."""

    dst_filename = os.path.join("TRANSCRIBED_" + src_filename.replace(".flac",".txt"))
    tmp_filepath = os.path.join("/tmp", dst_filename)

    with open(f'{tmp_filepath}', 'w') as file:
        for item in transcript:
            file.write(f'{item}\n')

    print(f'Processed transcript stored in: {tmp_filepath}')

    bucket = storage_client.get_bucket(DST_BUCKET_NAME)
    blob = bucket.blob(dst_filename)

    blob.upload_from_filename(tmp_filepath)

    return print(f'{tmp_filepath} uploaded to {DST_BUCKET_NAME}/{dst_filename}.')

def process_transcripts(data, context = None):
    """Orchestrator function that runs everything sequentially."""

    # Set up parameters
    FILE = data['name']
    SRC_BUCKET_NAME = data['bucket']

    print(f'Source Bucket: {SRC_BUCKET_NAME}')
    print(f'Source Filename: {FILE}')
    print(f'Destination Bucket: {DST_BUCKET_NAME}')

    print('Starting Process Transcript...')

    # Instantiate a Google Cloud Storage client 
    storage_client = storage.Client()

    # Process transcript from speech to text 
    
    gcs_uri = f"gs://{SRC_BUCKET_NAME}/{FILE}"
    transcript = transcribe_gcs(gcs_uri)

    # Upload data to gcs
    upload_file_to_gcs(FILE, transcript, storage_client, DST_BUCKET_NAME)

    print('Process Transcript Complete.')

# if __name__ == "__main__":
    
#     gcs_test_object = {
#         "name": "test_rec.json",
#         "bucket": "meeting-transcript-team13",
#     }
    
#     process_transcripts(gcs_test_object)

if __name__ == "__main__":
    
    gcs_test_object = {
        "name": "test_rec.flac",
        "bucket": "meeting-audio-team13",
    }
    # In Cloud Function set these as environment variables
    os.environ["DST_BUCKET_NAME"] = "meeting-transcript-team13"
    
    process_transcripts(gcs_test_object)