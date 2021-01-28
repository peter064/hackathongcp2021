from google.cloud import storage
import json
from string import punctuation
import spacy
import os


def load_file_from_gcs(storage_client, src_bucket_name: str, src_filename: str):
    
    bucket = storage_client.get_bucket(src_bucket_name)
    blob = bucket.blob(src_filename)
    
    # Download the contents of the blob as a bytes object
    data = blob.download_as_string(client=None)
    
    print(f'Loaded {src_filename} from {src_bucket_name}')
    return data


def get_sentences_from_transcript(bytes_object):
    # Decode bytes object to string and remove new lines
    transcript = bytes_object.decode('utf-8').replace('\n', '')
    
    # Load spacy model package "en_core_web_sm"
    nlp = spacy.load('en_core_web_sm')
    
    # Read sentences as strings into list
    about_transcript = nlp(transcript)
    sentences = [sent.text for sent in about_transcript.sents]
    
    return sentences


def get_sentences(data, keyword: str, ind_before: int, ind_after: int):
    
    transcript_list = get_sentences_from_transcript(data)
    
    # Return list of indices containing name parameter
    indices = [i for i, s in enumerate(transcript_list) if keyword in s]
    
    sentences = []
    
    for ind in indices:
        min_ind = ind - ind_before
        max_ind = ind + ind_after
        sentences.append(transcript_list[min_ind:max_ind])

    return sentences


def upload_file_to_gcs(storage_client, src_filepath: str, dst_bucket_name: str, dst_filename: str):
    """Uploads a file to the bucket."""
    
    bucket = storage_client.get_bucket(dst_bucket_name)
    
    blob = bucket.blob(dst_filename)

    blob.upload_from_filename(src_filepath)

    return print(f'{src_filepath} uploaded to {dst_bucket_name}/{dst_filename}.')


def upload_transcript_to_gcs(src_filename: str, 
                             transcript_number: int, 
                             transcript_list: list, 
                             title: str,
                             storage_client, 
                             dst_bucket_name: str):
    """"""
    dst_filename = os.path.join("PROCESSED_" + src_filename.replace('.txt', f'_{transcript_number}.json'))
    
    tmp_filepath = os.path.join("/tmp", dst_filename)

    with open(f'{tmp_filepath}', 'w') as f:
        json.dump({'file':src_filename, 'title': title, 'message_body': transcript_list}, f)
            
    print(f'Processed transcript stored in: {tmp_filepath}')
    
    return upload_file_to_gcs(storage_client, tmp_filepath, dst_bucket_name, dst_filename)
    

def create_title(processed_transcript: str, keyword: str):
    """Creates a relevant title for the alert depending on whether a question was asked to the user."""
    if '?' in ''.join(processed_transcript):
        return f'{keyword}, you have been asked a question'
    else:
        return f'{keyword}, your name has been mentioned'
    
    
def process_transcripts(data, context = None):
    
    # Set up parameters
    KEYWORD = os.environ.get('KEYWORD')
    SENTENCES_BEFORE = int(os.environ.get('SENTENCES_BEFORE'))
    SENTENCES_AFTER = int(os.environ.get('SENTENCES_AFTER'))
    FILE = data['name']
    SRC_BUCKET_NAME = data['bucket']
    DST_BUCKET_NAME = os.environ.get('DST_BUCKET_NAME')
    
    print(f'Source Bucket: {SRC_BUCKET_NAME}')
    print(f'Source Filename: {FILE}')
    print(f'Destination Bucket: {DST_BUCKET_NAME}')   
    
    print('Starting Process Transcript...')
    
    # Instantiate a Google Cloud Storage client and specify required bucket and file
    storage_client = storage.Client()
    
    # Get data from gcs
    transcript = load_file_from_gcs(storage_client, SRC_BUCKET_NAME, FILE)
    
    # Process data
    processed_transcript_list = get_sentences(transcript, KEYWORD, SENTENCES_BEFORE, SENTENCES_AFTER) 

    if len(processed_transcript_list) > 0:
        # Upload data to gcs
        for transcript_number, processed_transcript in enumerate(processed_transcript_list):
            title = create_title(processed_transcript, KEYWORD)
            upload_transcript_to_gcs(FILE, transcript_number, processed_transcript, title, storage_client, DST_BUCKET_NAME)
    else:
        print('No instance of keyword found.')
    
    print('Process Transcript Complete.')

if __name__ == "__main__":
    
    gcs_test_object = {
        "name": "multiple_speakers_punctuation_v4.txt",
        "bucket": "meeting-transcript-team13",
    }
    
    # In Cloud Function set these as environment variables
    os.environ["KEYWORD"] = "Christina"
    os.environ["SENTENCES_BEFORE"] = "2"
    os.environ["SENTENCES_AFTER"] = "2"
    os.environ["DST_BUCKET_NAME"] = "meeting-transcript-processed-team13"
    
    process_transcripts(gcs_test_object)