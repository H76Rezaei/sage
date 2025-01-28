from fastapi import UploadFile, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse, FileResponse, JSONResponse
from io import BytesIO
import ffmpeg
from pydub import AudioSegment
import json
import asyncio
from audio.speech import voice_to_text, new_tts
from TTS.api import TTS
from nltk.tokenize import sent_tokenize
import torch
import re
import nltk
from threading import Event
import subprocess
import os
from dotenv import load_dotenv
import soundfile as sf
import numpy as np

load_dotenv() 

nltk.download('punkt')

device= ("cuda" if torch.cuda.is_available() 
            else "mps" if torch.backends.mps.is_available() 
            else "cpu")

# Initialize Coqui TTS model for text-to-speech conversion
tts_model = TTS(model_name="tts_models/en/ljspeech/tacotron2-DDC").to(device)

# Global event to manage stream cancellation
cancel_event = asyncio.Event()

async def convert_to_wav(audio: UploadFile):
    """
    Convert input audio file to WAV format using ffmpeg.
    
    Args:
        audio (UploadFile): Input audio file to be converted
    
    Returns:
        BytesIO: Converted WAV audio in memory
    """
    try:
        # Read uploaded audio file
        audio_data = await audio.read()
        input_audio = BytesIO(audio_data)
        output_audio = BytesIO()

        # Use ffmpeg to convert audio to WAV format
        process = (
            ffmpeg
            .input('pipe:0')
            .output('pipe:1', format='wav')
            .run_async(pipe_stdin=True, pipe_stdout=True, pipe_stderr=True)
        )

        # Write and process input audio data
        stdout, stderr = process.communicate(input=input_audio.read())

        # Log any ffmpeg conversion errors
        if stderr:
            print(f"ffmpeg error: {stderr.decode()}")

        # Store converted audio in memory buffer
        output_audio.write(stdout)
        output_audio.seek(0)

        # Log converted audio size for debugging
        print(f"Converted audio size: {output_audio.getbuffer().nbytes} bytes")

        return output_audio
    except Exception as e:
        # Handle conversion errors
        raise HTTPException(status_code=500, detail="Error during conversion to WAV: " + str(e))

def convert_wav_to_mp3(wav_file, mp3_file):
    """
    Convert WAV audio file to MP3 format.
    
    Args:
        wav_file (str): Path to input WAV file
        mp3_file (str): Path to output MP3 file
    """
    # Use pydub to convert WAV to MP3
    audio = AudioSegment.from_wav(wav_file)
    audio.export(mp3_file, format="mp3")


def preprocess_text(text):
    """Preprocesses text for TTS to handle special characters and formatting."""

    text = text.replace("’", "'")  # Replace curly apostrophes
    text = text.replace("…", "...")  # Replace ellipsis character
    text = re.sub(r"[^\w\s.,?!]", "", text)  # Keep word chars, whitespace, and basic punctuation
    text = re.sub(r"\s+", " ", text).strip()  # Remove extra whitespace
    return text

async def conversation_audio(audio: UploadFile, chatbot):
    """
    Complete audio-to-audio conversation pipeline. (no streaming)
    
    Workflow:
    1. Convert audio to WAV
    2. Perform speech-to-text
    3. Generate text response
    4. Convert response to speech
    5. Return MP3 audio response
    
    Args:
        audio (UploadFile): Input audio file
        chatbot: Conversational AI companion
    
    Returns:
        FileResponse or JSONResponse
    """
    try:
        # Convert input audio to WAV
        wav_audio = await convert_to_wav(audio)  
        
        # Perform speech-to-text recognition
        stt_result = voice_to_text(wav_audio)
        if not stt_result["success"]:
            return JSONResponse(content={"error": stt_result["error"]}, status_code=400)

        # Extract transcribed text
        user_input = stt_result["text"]
        print(f"User said: {user_input}")

        # Generate AI response
        response_text = ""
        async for chunk in chatbot.stream_workflow_response(user_input):
            response_text += chunk

        print(f"Generated response: {response_text}")
        response_text = preprocess_text(response_text)
        print(f"Processed response: {response_text}")

        # Validate response text
        if not response_text.strip():
            raise ValueError("No text to speak")
        
        # Generate speech response using Coqui TTS
        output_filename = "response.wav"
        new_tts(response_text, filename=output_filename)

        # Convert response to MP3
        output_mp3_filename = "response.mp3"
        convert_wav_to_mp3(output_filename, output_mp3_filename)

        # Return MP3 audio file
        return FileResponse(output_mp3_filename, media_type='audio/mpeg', filename=output_mp3_filename)

    except Exception as e:
        # Handle any processing errors
        return JSONResponse(content={"error": f"Error in audio processing: {str(e)}"}, status_code=500)

async def cancel_stream():
    """
    Trigger cancellation of ongoing audio processing.
    
    Returns:
        JSONResponse confirming cancellation
    """
    # Set global cancellation event
    cancel_event.set()
    print("Cancel event triggered")
    return JSONResponse(content={"message": "Processing cancelled."}, status_code=200)

async def conversation_audio_stream(audio: UploadFile, background_tasks: BackgroundTasks, chatbot):
    """
    Streaming audio-to-audio conversation with cancellation support.
    
    Workflow:
    1. Convert audio to WAV
    2. Perform speech-to-text
    3. Generate text response
    4. Stream text-to-speech audio chunks
    
    Args:
        audio (UploadFile): Input audio file
        background_tasks (BackgroundTasks): FastAPI background tasks
        chatbot: Conversational AI companion
    
    Returns:
        StreamingResponse of audio chunks
    """
    # Reset cancellation flag
    cancel_event.clear()

    try:
        # Convert input audio to WAV
        wav_audio = await convert_to_wav(audio)
        
        # Perform speech-to-text recognition
        stt_result = voice_to_text(wav_audio)
        if not stt_result["success"]:
            return JSONResponse(content={"error": stt_result["error"]}, status_code=400)
        
        # Extract transcribed text
        user_input = stt_result["text"]
        print(f"User said: {user_input}")
        
        # Generate AI response
        response_text = ""
        async for chunk in chatbot.stream_workflow_response(user_input):
            # Check for cancellation during response generation
            if cancel_event.is_set():
                print("Processing cancelled")
                return
            response_text += chunk
        
        response_text = preprocess_text(response_text)
        print(f"Processed response: {response_text}")
        # Tokenize response into sentences
        sentences = sent_tokenize(response_text)
        print(f"Generated sentences: {sentences}")
        
        # Stream audio chunks
        async def generate_wav_chunks():
            # Check for early cancellation
            if cancel_event.is_set():
                print("Chunk generation cancelled")
                return

            # Generate audio for each sentence
            for sentence in sentences:
                # Check cancellation between sentences
                if cancel_event.is_set():
                    print("Chunk generation cancelled")
                    return

                # Convert sentence to audio
                buffer = BytesIO()
                tts_model.tts_to_file(text=sentence, file_path=buffer)
                buffer.seek(0)
                chunk_data = buffer.read()
                max_chunk_size = 100 * 1024  # 100 KB chunk size

                # Yield audio chunks
                for i in range(0, len(chunk_data), max_chunk_size):
                    # Check cancellation during chunk generation
                    if cancel_event.is_set():
                        print("Streaming cancelled during chunk generation")
                        return
                    
                    chunk = chunk_data[i:i+max_chunk_size]
                    # Log first chunk header for debugging
                    if i == 0:
                        print(f"First chunk includes header: {chunk[:4] == b'RIFF'}")
                    yield chunk
               
        # Return streaming WAV audio response
        return StreamingResponse(generate_wav_chunks(), media_type="audio/wav")
    
    except Exception as e:    
        # Handle any processing errors
        print(f"Error in audio processing: {str(e)}")
        import traceback
        traceback.print_exc()
        return JSONResponse(content={"error": f"Error in audio processing: {str(e)}"}, status_code=500)
    


async def generate_audio_async(text, output_queue, cancel_event):
    try:
        kokoro_venv_path = os.getenv("KOKORO_VENV_PATH")
        print(f"KOKORO_VENV_PATH: {kokoro_venv_path}")  # Get path from env variable
        if not kokoro_venv_path:
            raise ValueError("KOKORO_VENV_PATH environment variable not set.")

        python_executable = os.path.join(kokoro_venv_path, "Scripts", "python.exe")  
        print(f"Using Kokoro Python: {python_executable}") 
        if not os.path.exists(python_executable):
            raise ValueError(f"Python executable not found in Kokoro venv: {kokoro_venv_path}")
        
        audio_dir = os.path.dirname(os.path.abspath(__file__))  
        print(f"audio dir: {audio_dir}")
        print(os.path.join(audio_dir, "kokoro_bridge.py"))

        process = await asyncio.create_subprocess_exec(
            python_executable,
            os.path.join(audio_dir, "kokoro_bridge.py"),
            text,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=audio_dir,
        )

        audio_data = await process.stdout.read() # Read all bytes at once
        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            error_message = stderr.decode() if stderr else "Kokoro TTS failed"
            print(f"Kokoro TTS error: {error_message}", file=sys.stderr) # Print errors to stderr
            output_queue.put_nowait(json.dumps({"error": error_message}).encode()) # Still send errors as JSON
            return

        if not audio_data:
            print("No audio data received from Kokoro.", file=sys.stderr)
            output_queue.put_nowait(json.dumps({"error": "No audio data received"}).encode())
            return

        output_queue.put_nowait(audio_data)
        output_queue.put_nowait(b"__END__")

    except Exception as e:
        print(f"Error in generate_audio_async: {e}")
        output_queue.put_nowait(json.dumps({"error": str(e)}).encode())

async def generate_wav_chunks(sentences, cancel_event):  
    for sentence in sentences:
        if cancel_event.is_set():
            print("Chunk generation cancelled.")
            return

        output_queue = asyncio.Queue()
        task = asyncio.create_task(generate_audio_async(sentence, output_queue, cancel_event))

       
        try:
            item = await output_queue.get()
            samples, sample_rate = sf.read(BytesIO(item))
            if isinstance(item, bytes):
                if item == b"__END__":
                    continue  # Skip the __END__ marker
                try:
                    # 1. Try to load as JSON to check for errors
                    error_dict = json.loads(item.decode())
                    if "error" in error_dict:
                        print(f"Kokoro error: {error_dict['error']}")
                        yield item # Yield the error as is
                        continue  # Skip to the next sentence
                except (json.JSONDecodeError, UnicodeDecodeError):
                    pass  # It's audio data

                # 2. Process audio data:
                try:
                    # Get sample rate and other info (you might need to adjust this)
                    samples, sample_rate = sf.read(BytesIO(item))  # Read the complete audio data
                    print(f"Sample Rate: {sample_rate}, Data Shape: {samples.shape}, Data Type: {samples.dtype}")

                    # Ensure it is 16 bit
                    if samples.dtype != np.int16:
                        samples = (samples * 32767).astype(np.int16) # convert to int16

                    audio_buffer = BytesIO()
                    sf.write(audio_buffer, samples, sample_rate, format='WAV')
                    audio_buffer.seek(0)
                    wav_data = audio_buffer.getvalue()
                    yield wav_data  # Yield the complete wav data

                except Exception as e:
                    print(f"Error processing audio with soundfile: {e}")
                    yield json.dumps({"error": f"Audio processing error: {str(e)}"}).encode()

        except Exception as e:
            print(f"Error during streaming: {e}")
            yield json.dumps({"error": str(e)}).encode()
        finally:
            await output_queue.join()
            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

async def conversation_audio_stream_kokoro(audio: UploadFile, background_tasks: BackgroundTasks, chatbot):
    # Reset cancellation flag
    cancel_event.clear()

    try:
        wav_audio = await convert_to_wav(audio)
        stt_result = voice_to_text(wav_audio)
        if not stt_result["success"]:
            return JSONResponse(content={"error": stt_result["error"]}, status_code=400)

        user_input = stt_result["text"]
        print(f"User said: {user_input}")

        response_text = ""
        async for chunk in chatbot.stream_workflow_response(user_input):
            if cancel_event.is_set():
                print("Processing cancelled")
                return  # Return immediately if cancelled
            response_text += chunk

        response_text = preprocess_text(response_text)
        print(f"Processed response: {response_text}")

        sentences = sent_tokenize(response_text)
        print(f"Generated sentences: {sentences}")

        async def generate():
            async for chunk in generate_wav_chunks(sentences, cancel_event): # Pass cancel_event
                if cancel_event.is_set(): # Check cancellation during chunk generation
                    print("Streaming cancelled during chunk generation")
                    return
                yield chunk

        return StreamingResponse(generate(), media_type="audio/wav")

    except Exception as e:
        return JSONResponse(content={"error": f"Error in audio processing: {str(e)}"}, status_code=500)