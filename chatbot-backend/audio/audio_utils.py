from fastapi import UploadFile, BackgroundTasks, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse, FileResponse
from pydub import AudioSegment
from TTS.api import TTS
from nltk.tokenize import sent_tokenize
from io import BytesIO
import ffmpeg
import asyncio
import os
from companion.digital_companion import DigitalCompanion
from audio.speech import voice_to_text, new_tts

tts_model = TTS(model_name="tts_models/en/ljspeech/tacotron2-DDC")
chatbot = DigitalCompanion()
cancel_event = asyncio.Event()


# Convert audio to WAV format
async def convert_to_wav(audio: UploadFile):
    try:
        audio_data = await audio.read()
        input_audio = BytesIO(audio_data)
        output_audio = BytesIO()

        process = (
            ffmpeg
            .input('pipe:0')
            .output('pipe:1', format='wav')
            .run_async(pipe_stdin=True, pipe_stdout=True, pipe_stderr=True)
        )

        stdout, stderr = process.communicate(input=input_audio.read())
        if stderr:
            print(f"ffmpeg error: {stderr.decode()}")

        output_audio.write(stdout)
        output_audio.seek(0)
        return output_audio
    except Exception as e:
        raise HTTPException(status_code=500, detail="Error during conversion to WAV: " + str(e))


# Convert WAV to MP3
def convert_wav_to_mp3(wav_file, mp3_file):
    audio = AudioSegment.from_wav(wav_file)
    audio.export(mp3_file, format="mp3")


# Conversation Audio Endpoint Logic
async def conversation_audio(audio: UploadFile):
    try:
        wav_audio = await convert_to_wav(audio)
        stt_result = voice_to_text(wav_audio)
        if not stt_result["success"]:
            return JSONResponse(content={"error": stt_result["error"]}, status_code=400)

        user_input = stt_result["text"]
        print(f"User said: {user_input}")

        response_text = ""
        async for chunk in chatbot.stream_workflow_response(user_input):
            response_text += chunk

        if not response_text.strip():
            raise ValueError("No text to speak")

        output_filename = "response.wav"
        new_tts(response_text, filename=output_filename)

        output_mp3_filename = "response.mp3"
        convert_wav_to_mp3(output_filename, output_mp3_filename)

        return FileResponse(output_mp3_filename, media_type='audio/mpeg', filename=output_mp3_filename)

    except Exception as e:
        return JSONResponse(content={"error": f"Error in audio processing: {str(e)}"}, status_code=500)


# Cancel Stream Endpoint Logic
async def cancel_stream():
    cancel_event.set()
    print("Cancel event triggered")
    return JSONResponse(content={"message": "Processing cancelled."}, status_code=200)


# Conversation Audio Stream Endpoint Logic
async def conversation_audio_stream(audio: UploadFile, background_tasks: BackgroundTasks):
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
                return
            response_text += chunk

        sentences = sent_tokenize(response_text)
        print(f"Generated sentences: {sentences}")

        async def generate_wav_chunks():
            for sentence in sentences:
                if cancel_event.is_set():
                    print("Chunk generation cancelled")
                    return
                buffer = BytesIO()
                tts_model.tts_to_file(text=sentence, file_path=buffer)
                buffer.seek(0)
                chunk_data = buffer.read()
                max_chunk_size = 100 * 1024

                for i in range(0, len(chunk_data), max_chunk_size):
                    if cancel_event.is_set():
                        print("Streaming cancelled during chunk generation")
                        return
                    yield chunk

        return StreamingResponse(generate_wav_chunks(), media_type="audio/wav")

    except Exception as e:
        print(f"Error in audio processing: {str(e)}")
        return JSONResponse(content={"error": f"Error in audio processing: {str(e)}"}, status_code=500)