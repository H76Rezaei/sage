import os
from io import BytesIO
from fastapi import UploadFile
from gtts import gTTS
from playsound import playsound
import whisper


# Load the Whisper model (choose 'tiny', 'base', 'small',Large )
model = whisper.load_model("small")


def voice_to_text(audio_data: BytesIO):
    """
    Convert audio to text using OpenAI's Whisper model.
    """
    try:
        # Save the audio data to a temporary file
        with open("temp_audio.wav", "wb") as f:
            f.write(audio_data.getvalue())

        # Use the Whisper model to transcribe the audio
        print("Recognizing speech using Whisper...")
        result = model.transcribe("temp_audio.wav")
        text = result.get("text", "")

        # Clean up temporary file
        os.remove("temp_audio.wav")

        if text:
            return {"success": True, "text": text}
        else:
            return {"success": False, "error": "Could not recognize text from audio."}

    except Exception as e:
        return {"success": False, "error": f"An error occurred: {str(e)}"}


def text_to_speech(text, filename='response.mp3', play_sound=False):
    """
    Convert text to speech and save as an MP3 file.
    Optionally, play the sound after saving.
    """
    try:
        tts = gTTS(text=text, lang='en')
        tts.save(filename)

        print(f"Audio file saved as: {filename}")

        if os.path.exists(filename):
            print(f"Audio file {filename} exists.")
        else:
            print(f"Audio file {filename} does not exist.")

        if play_sound:
            try:
                playsound(filename)
            except Exception as e:
                print(f"Error playing sound: {e}")
    except Exception as e:
        print(f"Error converting text to speech: {e}")

