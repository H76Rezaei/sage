from fastapi import UploadFile, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse, JSONResponse
from io import BytesIO
import ffmpeg
from pydub import AudioSegment
import asyncio
from audio.stt_utils import voice_to_text
from nltk.tokenize import sent_tokenize
import torch
import re
import nltk
import os
from dotenv import load_dotenv
import soundfile as sf
import numpy as np
import logging
import asyncio
from fastapi import UploadFile, BackgroundTasks
import soundfile as sf


from audio.persistent_process import KokoroTTSWorker

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

load_dotenv() 

nltk.download('punkt')

device= ("cuda" if torch.cuda.is_available() 
            else "mps" if torch.backends.mps.is_available() 
            else "cpu")



# Global event to manage stream cancellation
cancel_event = asyncio.Event()

async def convert_to_wav(audio: UploadFile):
    """
    Convert input audio file to WAV format using ffmpeg only if necessary.
    """
    try:
        audio_data = await audio.read()
        input_audio = BytesIO(audio_data)

        # If the uploaded file is already WAV, return it directly.
        if audio.content_type == "audio/wav":
            logger.debug("Uploaded audio is already in WAV format.")
            return input_audio

        output_audio = BytesIO()
        process = (
            ffmpeg
            .input('pipe:0')
            .output('pipe:1', format='wav')
            .run_async(pipe_stdin=True, pipe_stdout=True, pipe_stderr=True)
        )
        stdout, stderr = process.communicate(input=input_audio.read())

        if stderr:
            logger.debug(f"ffmpeg error: {stderr.decode()}")
        output_audio.write(stdout)
        output_audio.seek(0)
        logger.debug(f"Converted audio size: {output_audio.getbuffer().nbytes} bytes")
        return output_audio
    except Exception as e:
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


async def cancel_stream():
    """
    Trigger cancellation of ongoing audio processing.
    
    Returns:
        JSONResponse confirming cancellation
    """
    # Set global cancellation event
    cancel_event.set()
    #print("Cancel event triggered")
    return JSONResponse(content={"message": "Processing cancelled."}, status_code=200)

  
# Create a single global instance
tts_worker = KokoroTTSWorker()

async def generate_audio_async(text):
    """Generate audio for a single chunk of text"""
    try:
        kokoro_venv_path = os.getenv("KOKORO_VENV_PATH")
        python_executable = os.path.join(kokoro_venv_path, "Scripts", "python.exe")
        audio_dir = os.path.dirname(os.path.abspath(__file__))
        
        #print(f"Generating audio for: {text}")
        if cancel_event.is_set():
                return
        process = await asyncio.create_subprocess_exec(
            python_executable,
            os.path.join(audio_dir, "kokoro_bridge.py"),
            text,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=audio_dir,
        )

        if cancel_event.is_set():
                return
        
        stdout, stderr = await process.communicate()
        
        if stderr:
            #print(f"Error from Kokoro: {stderr.decode()}")
            return None
            
        if not stdout:
            #print("No audio data received")
            return None
        
        if cancel_event.is_set():
                return    
        # Convert to WAV format
        audio_buffer = BytesIO(stdout)
        samples, sample_rate = sf.read(audio_buffer)
        
        if samples.dtype != np.int16:
            samples = (samples * 32767).astype(np.int16)
        
        output_buffer = BytesIO()
        sf.write(output_buffer, samples, sample_rate, format='WAV', subtype='PCM_16')
        output_buffer.seek(0)

        if cancel_event.is_set():
                return
        
        return output_buffer.getvalue()
        
    except Exception as e:
        print(f"Error generating audio: {e}")
        return None

async def stream_audio_chunks(sentences, cancel_event):
    """Stream audio chunks with proper WAV headers"""
    if cancel_event.is_set():
        return
    try:
        await tts_worker.ensure_worker_ready()
        #print(f"Starting to process {len(sentences)} sentences")
        if cancel_event.is_set():
            return

        for i, sentence in enumerate(sentences):
            if cancel_event.is_set():
                return
            try:
                #print(f"Processing sentence {i+1}/{len(sentences)}: {sentence}")
                audio_data = await tts_worker.generate_audio(sentence)
                if cancel_event.is_set():
                    return

                if audio_data:
                    # Instead of re-reading and re-writing the audio,
                    # yield the received WAV bytes directly.
                    #print(f"Processed audio chunk: {len(audio_data)} bytes")
                    yield audio_data
                    #print(f"Chunk {i+1} sent to frontend")
                else:
                    print(f"No audio data generated for sentence {i+1}")
            except Exception as e:
                print(f"Error processing chunk {i+1}: {e}")
                continue

    except Exception as e:
        print(f"Error in stream_audio_chunks: {e}")
        raise

async def conversation_audio_stream_kokoro(audio: UploadFile, background_tasks: BackgroundTasks, chatbot):
    cancel_event.clear()
    try:
        wav_audio = await convert_to_wav(audio)
        if cancel_event.is_set():
                return
        stt_result = voice_to_text(wav_audio)
        if cancel_event.is_set():
                return
        if not stt_result["success"]:
            return JSONResponse(content={"error": stt_result["error"]}, status_code=400)
            
        user_input = stt_result["text"]
        #print(f"Processing user input: {user_input}")

        if cancel_event.is_set():
                return
        # Collect the entire response first
        response_text = ""
        async for chunk in chatbot.stream_workflow_response(user_input):
            if cancel_event.is_set():
                return
            response_text += chunk
            
        if cancel_event.is_set():
                return    
        #response_text = preprocess_text(response_text)
        sentences = sent_tokenize(response_text)

        if cancel_event.is_set():
                return
        
        return StreamingResponse(
            stream_audio_chunks(sentences, cancel_event),
            media_type="audio/wav",
            headers={
                "X-Content-Type-Options": "nosniff",
                "Content-Disposition": "inline"
            }
        )
    except Exception as e:
        print(f"Error in conversation stream: {e}")
        return JSONResponse(content={"error": str(e)}, status_code=500)