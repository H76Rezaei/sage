from kokoro_onnx import Kokoro
import sys
import os
import soundfile as sf
from io import BytesIO
from pydub import AudioSegment
import json
import numpy as np



model = Kokoro("kokoro-v0_19.onnx", "voices.bin")

def run_server():
    """Run as a persistent TTS server process"""
    print("Initializing Kokoro TTS server...", file=sys.stderr)
    model = Kokoro("kokoro-v0_19.onnx", "voices.bin")
    print("Model loaded successfully", file=sys.stderr)

    stdin = os.fdopen(sys.stdin.fileno(), 'rb', buffering=0)
    stdout = os.fdopen(sys.stdout.fileno(), 'wb', buffering=0)

    while True:
        try:
            length_bytes = stdin.read(4)
            if not length_bytes:
                print("Input stream closed", file=sys.stderr)
                break

            msg_length = int.from_bytes(length_bytes, 'big')
            message = stdin.read(msg_length).decode('utf-8')
            request = json.loads(message)

            if request["type"] == "ping":
                stdout.write((0).to_bytes(4, 'big'))
                stdout.flush()
                continue

            if request["type"] == "generate":
                text = request["text"]
                #print(f"Generating audio for: {text}", file=sys.stderr)
                
                samples, sample_rate = model.create(
                    text,
                    voice="af_sky",
                    speed=1.0,
                    lang="en-us"
                )

                if isinstance(samples, bytes):
                    # Assume samples is already a WAV file.
                    audio_data = samples
                else:
                    # Convert raw samples to WAV.
                    if samples.dtype != np.int16:
                        samples = (samples * 32767).astype(np.int16)
                    audio_buffer = BytesIO()
                    sf.write(audio_buffer, samples, sample_rate, format='WAV', subtype='PCM_16')
                    audio_data = audio_buffer.getvalue()

                """
                # Normalize and convert to int16
                if samples.dtype != np.int16:
                    samples = (samples * 32767).astype(np.int16)

                # Generate WAV in memory
                audio_buffer = BytesIO()
                sf.write(audio_buffer, samples, sample_rate, format='WAV', subtype='PCM_16')
                audio_data = audio_buffer.getvalue()
                """

                #print(f"Generated audio size: {len(audio_data)} bytes", file=sys.stderr)

                # Send full size first
                stdout.write(len(audio_data).to_bytes(4, 'big'))
                
                # Send data in chunks to avoid buffer issues
                chunk_size = 32768
                for i in range(0, len(audio_data), chunk_size):
                    chunk = audio_data[i:i + chunk_size]
                    stdout.write(chunk)
                    stdout.flush()
                
                #print(f"Audio data sent successfully", file=sys.stderr)

        except Exception as e:
            print(f"Server error: {e}", file=sys.stderr)
            error_msg = json.dumps({"error": str(e)}).encode('utf-8')
            stdout.write(len(error_msg).to_bytes(4, 'big'))
            stdout.write(error_msg)
            stdout.flush()

if __name__ == "__main__":
    if "--server" in sys.argv:
        run_server()
    else:
        # Original single-request mode
        if len(sys.argv) < 2:
            print("Usage: python kokoro_bridge.py <text>", file=sys.stderr)
            sys.exit(1)
        
        input_text = sys.argv[1]
        model = Kokoro("kokoro-v0_19.onnx", "voices.bin")
        samples, sample_rate = model.create(input_text, voice="af_sky", speed=1.0, lang="en-us")
        
        audio_buffer = BytesIO()
        sf.write(audio_buffer, samples, sample_rate, format='WAV')
        sys.stdout.buffer.write(audio_buffer.getvalue())