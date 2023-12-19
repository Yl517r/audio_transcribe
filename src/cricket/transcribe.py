import time
from pydub import AudioSegment
import azure.cognitiveservices.speech as speechsdk
from dotenv import load_dotenv
import os

load_dotenv()

subscription_key = os.getenv("SPEECH_KEY")
region = os.getenv("SPEECH_REGION")

# Folder paths for input and output
input_folder = "/Users/yangliu/Downloads/test_input"
output_folder = "/Users/yangliu/Downloads/test_output"

transcriptions = []


def convert_audio(input_file, output_file):
    try:
        audio = AudioSegment.from_file(input_file)
    except Exception as e:
        print(f"Failed to load audio file {input_file}. Error: {e}")
        return False

    audio = audio.set_frame_rate(16000)  # Set frame rate to 16 kHz
    audio = audio.set_channels(1)  # Set audio to mono
    audio.export(output_file, format="wav")  # Export audio in WAV format
    return True


def conversation_transcriber_recognition_canceled_cb(evt: speechsdk.SessionEventArgs):
    print('Canceled event')


def conversation_transcriber_session_stopped_cb(evt: speechsdk.SessionEventArgs):
    print('SessionStopped event')


def conversation_transcriber_transcribed_cb(evt: speechsdk.SpeechRecognitionEventArgs):
    try:
        if evt.result.reason == speechsdk.ResultReason.RecognizedSpeech and evt.result.text.strip() != '':
            speaker_id = "Speaker-{}".format(
                evt.result.speaker_id) if evt.result.speaker_id != "Unknown" else "Unknown Speaker"
            transcribed_text = '{}: {}'.format(speaker_id, evt.result.text)
            print(transcribed_text)
            transcriptions.append(transcribed_text)
        elif evt.result.reason == speechsdk.ResultReason.NoMatch:
            print('NOMATCH: Speech could not be transcribed: {}'.format(evt.result.no_match_details))
        else:
            print('UNKNOWN: Unexpected result reason: {}'.format(evt.result.reason))

    except Exception as e:
        print('Error occurred during transcription: {}'.format(e))


def conversation_transcriber_session_started_cb(evt: speechsdk.SessionEventArgs):
    print('SessionStarted event')


def recognize_from_file(input_file, output_file):
    try:
        speech_config = speechsdk.SpeechConfig(subscription=subscription_key, region=region)
        speech_config.speech_recognition_language = "es-ES"

        audio_config = speechsdk.audio.AudioConfig(filename=input_file)
        conversation_transcriber = speechsdk.transcription.ConversationTranscriber(speech_config=speech_config,
                                                                                   audio_config=audio_config)
    except Exception as e:
        print(f"Failed to initialize ConversationTranscriber. Error: {e}")
        return

    transcribing_stop = False

    def stop_cb(evt: speechsdk.SessionEventArgs):
        print('CLOSING on {}'.format(evt))
        nonlocal transcribing_stop
        transcribing_stop = True

    conversation_transcriber.transcribed.connect(conversation_transcriber_transcribed_cb)
    conversation_transcriber.session_started.connect(conversation_transcriber_session_started_cb)
    conversation_transcriber.session_stopped.connect(conversation_transcriber_session_stopped_cb)
    conversation_transcriber.canceled.connect(conversation_transcriber_recognition_canceled_cb)
    conversation_transcriber.session_stopped.connect(stop_cb)
    conversation_transcriber.canceled.connect(stop_cb)

    try:
        start_time = time.time()  # Record start time

        future = conversation_transcriber.start_transcribing_async()
        future.get()

        while not transcribing_stop:
            time.sleep(.5)

        conversation_transcriber.stop_transcribing_async()

        end_time = time.time()  # Record end time

        print(f"Transcribing time for {input_file}: {end_time - start_time} seconds")  # Print elapsed time
    except Exception as e:
        print(f"Failed to transcribe file {input_file}. Error: {e}")

    return "\n".join(transcriptions)


def convert_and_transcribe_files():
    for filename in os.listdir(input_folder):
        if filename.endswith(".wav"):
            input_file = os.path.join(input_folder, filename)
            converted_file = os.path.join(input_folder, f"converted_{filename}")
            output_file = os.path.join(output_folder, f"{os.path.splitext(filename)[0]}.txt")

            try:
                # Convert the audio file
                convert_audio(input_file, converted_file)

                transcriptions.clear()
                # Transcribe the converted audio file
                transcribed_text = recognize_from_file(converted_file, output_file)

                with open(output_file, 'w') as f:
                    f.write(transcribed_text)

                # Optionally, delete the converted file after transcription
                os.remove(converted_file)

            except Exception as err:
                print(f"Encountered exception for file {input_file}. {err}")


convert_and_transcribe_files()