from kokoro_onnx import Kokoro
import sys
import os
import soundfile as sf  # Library to save audio as .wav files

def generate_audio(text, output_file):
    # Initialize Kokoro ONNX TTS model with the model and voices paths
    model = Kokoro("kokoro-v0_19.onnx", "voices.bin")

    # Generate audio samples and sample rate from text
    samples, sample_rate = model.create(
        text, voice="af_nicole", speed=1.0, lang="en-us"
    )

    # Save audio to the output WAV file
    sf.write(output_file, samples, sample_rate)
    print(f"Audio saved to {output_file}")

if __name__ == "__main__":
    # Ensure the correct number of arguments are passed
    if len(sys.argv) < 3:
        print("Usage: python kokoro_bridge.py <text> <output_file>")
        sys.exit(1)

    # Read input text and output file from command-line arguments
    input_text = sys.argv[1]
    output_file = sys.argv[2]

    # Ensure the output directory exists
    output_dir = os.path.dirname(output_file)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # Generate audio
    generate_audio(input_text, output_file)
