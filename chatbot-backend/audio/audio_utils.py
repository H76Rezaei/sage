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

# Initialize Coqui TTS model for text-to-speech conversion
tts_model = TTS(model_name="tts_models/en/ljspeech/tacotron2-DDC")

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