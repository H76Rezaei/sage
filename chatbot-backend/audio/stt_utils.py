import speech_recognition as sr
from io import BytesIO
from pydub import AudioSegment
import librosa
import numpy as np
import torch
from faster_whisper import WhisperModel

# Determine device
device = (
    "cuda" if torch.cuda.is_available()
    #else "mps" if torch.backends.mps.is_available()
    else "cpu"
)

# Set compute_type based on device.
# For GPU (cuda/mps): float16, and for CPU: int8 
if device in ["cuda", "mps"]:
    compute_type = "float16"
else:
    compute_type = "int8"

# Load the Faster-Whisper model (model size: tiny, base, small, large)
model = WhisperModel("base", device=device, compute_type=compute_type)

#print("whisper device is:", device)


def downsample_audio(audio_data: BytesIO) -> BytesIO:
    """
    Downsample audio to 16kHz mono for faster processing.
    """
    audio_data.seek(0)
    audio = AudioSegment.from_file(audio_data)
    audio = audio.set_frame_rate(16000).set_channels(1)

    output_buffer = BytesIO()
    audio.export(output_buffer, format="wav")
    output_buffer.seek(0)
    return output_buffer



def voice_to_text(audio_data: BytesIO):
    """
    Convert audio to text using Faster Whisper model
    """
    try:
        # Downsample the audio to 16kHz mono
        audio_data = downsample_audio(audio_data)

        # Load the audio as a waveform
        y, sr = librosa.load(audio_data, sr=16000, mono=True)

        # Transcribe using Faster Whisper
        segments, _ = model.transcribe(y, beam_size=3)
        
        # Combine all segments
        text = " ".join([segment.text for segment in segments])

        if text:
            return {"success": True, "text": text}
        else:
            return {"success": False, "error": "Could not recognize text from audio."}

    except Exception as e:
        return {"success": False, "error": f"An error occurred: {str(e)}"}