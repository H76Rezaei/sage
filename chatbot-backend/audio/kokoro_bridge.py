from kokoro_onnx import Kokoro
import sys
import os
import soundfile as sf
from io import BytesIO
from pydub import AudioSegment

def generate_audio(text):
    model = Kokoro("kokoro-v0_19.onnx", "voices.bin") # Initialize Kokoro (once per process)
    samples, sample_rate = model.create(text, voice="af_nicole", speed=1.0, lang="en-us")
    buffer = BytesIO()
    audio_segment = AudioSegment(samples.tobytes(), frame_rate=sample_rate, sample_width=samples.dtype.itemsize, channels=1) # Assuming mono audio
    audio_segment.export(buffer, format="wav")
    buffer.seek(0)
    audio_bytes = buffer.getvalue()
    return audio_bytes

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python kokoro_bridge.py <text>")
        sys.exit(1)

    input_text = sys.argv[1]
    audio_bytes = generate_audio(input_text)

    sys.stdout.buffer.write(audio_bytes) # Write audio bytes to stdout