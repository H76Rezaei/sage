from kokoro_onnx import Kokoro
import sys
import os
import soundfile as sf
from io import BytesIO
from pydub import AudioSegment
import json
import numpy as np

def generate_audio(text):
    try:
        model = Kokoro("kokoro-v0_19.onnx", "voices.bin")
        samples, sample_rate = model.create(text, voice="af_nicole", speed=1.0, lang="en-us")

        samples = (samples * 32767).astype(np.int16)
        if samples.ndim > 1:
            samples = np.mean(samples, axis=1)

        audio_buffer = BytesIO()  # Use BytesIO to store audio in memory
        sf.write(audio_buffer, samples, sample_rate, format='WAV')
        audio_buffer.seek(0)
        audio_bytes = audio_buffer.getvalue()

        sys.stdout.buffer.write(audio_bytes)  # Write raw bytes to stdout
        sys.stdout.buffer.write(b"\n")
        return None  # No text message to return

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)  # Print errors to stderr
        return f"Error: {e}"  # Return error message (for debugging)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python kokoro_bridge.py <text>", file=sys.stderr)
        sys.exit(1)

    input_text = sys.argv[1]
    result = generate_audio(input_text)
    if result:  # If there was an error
        print(result, file=sys.stderr) # Print the error to stderr
        sys.exit(1) # Indicate failure