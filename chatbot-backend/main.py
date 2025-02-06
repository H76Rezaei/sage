from fastapi import FastAPI, Request, BackgroundTasks
from fastapi.responses import StreamingResponse, JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
import json
#from llama.ChatBotClass_new import DigitalCompanion
#from llama.generation import stream_generation
#from llama.model_manager import get_model_and_tokenizer
#from llama.prompt_manager import get_initial_prompts
from fastapi import FastAPI, Request, UploadFile ,Depends
from fastapi.responses import StreamingResponse, JSONResponse
from speech import  voice_to_text , text_to_speech, new_tts, cashed
from TTS.api import TTS
from nltk.tokenize import sent_tokenize
import os
from companion.digital_companion import DigitalCompanion
from pydub import AudioSegment
from io import BytesIO
from fastapi import UploadFile, File, HTTPException
from fastapi.responses import StreamingResponse
import ffmpeg

from threading import Thread
import time
import io
import wave
import asyncio




tts_model = TTS(model_name="tts_models/en/ljspeech/tacotron2-DDC")

chatbot = DigitalCompanion()

#llama model and tokenizer
#model, tokenizer = get_model_and_tokenizer()
app = FastAPI()


#########################################################################
# from user.user import router as user_router
from User.user import router as user_router



import jwt
from fastapi.security import OAuth2PasswordBearer
# from jwt.exceptions import DecodeError







SECRET_KEY = os.environ.get("SECRET_KEY", "your_secret_key")
ALGORITHM = "HS256"

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/user/login")

import jwt

def get_current_user_id(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("user_id")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid authentication credentials")
        return user_id
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid authentication credentials")







app.include_router(user_router, prefix="/user", tags=["User"])




#----------------------------------------
# from fastapi import Depends, HTTPException
# from auth import register_user, login_user
# from profile import get_profile, update_profile
# from fastapi.security import OAuth2PasswordBearer


# oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
# def get_current_user_id(token: str = Depends(oauth2_scheme)):
#     try:
#         payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
#         user_id = payload.get("user_id")
#         if user_id is None:
#             raise HTTPException(status_code=401, detail="Invalid authentication credentials")
#         return user_id
#     except JWTError:
#         raise HTTPException(status_code=401, detail="Invalid authentication credentials")

# @app.post("/register")
# def register(first_name: str, last_name: str, email: str, password: str):
#     return register_user(first_name, last_name, email, password)

# @app.post("/login")
# def login(email: str, password: str):
#     return login_user(email, password)

# @app.get("/profile")
# def profile(current_user_id: int = Depends(get_current_user_id)):
#     return get_profile(current_user_id)

# @app.put("/profile")
# def update_profile_endpoint(current_user_id: int = Depends(get_current_user_id),
#                             first_name: str = None, last_name: str = None,
#                             phone_number: str = None, birth_date: str = None):
#     return update_profile(current_user_id, first_name, last_name, phone_number, birth_date)

#----------------------------------------------------------------------------------------------------



# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)



# Define the function to convert audio to WAV using ffmpeg
async def convert_to_wav(audio: UploadFile):
    try:
        audio_data = await audio.read()
        input_audio = BytesIO(audio_data)
        output_audio = BytesIO()

        # Use ffmpeg to convert the input audio to WAV format
        process = (
            ffmpeg
            .input('pipe:0')
            .output('pipe:1', format='wav')
            .run_async(pipe_stdin=True, pipe_stdout=True, pipe_stderr=True)
        )

        # Write the input audio data to the process
        stdout, stderr = process.communicate(input=input_audio.read())

        # Log any errors from ffmpeg
        if stderr:
            print(f"ffmpeg error: {stderr.decode()}")

        # Write the output audio data to the BytesIO object
        output_audio.write(stdout)
        output_audio.seek(0)

        # Log the size of the output audio
        print(f"Converted audio size: {output_audio.getbuffer().nbytes} bytes")

        return output_audio
    except Exception as e:
        raise HTTPException(status_code=500, detail="Error during conversion to WAV: " + str(e))
    


def convert_wav_to_mp3(wav_file, mp3_file):
    audio = AudioSegment.from_wav(wav_file)
    audio.export(mp3_file, format="mp3")


@app.post("/conversation")
async def conversation(request: Request):
    body = await request.json()
    user_input = body.get("message")
    
    async def response_stream():
        async for token in chatbot.stream_workflow_response(user_input):
            yield f"data: {json.dumps({'response': token, 'is_final': False})}\n\n"
        yield f"data: {json.dumps({'response': '', 'is_final': True})}\n\n"
        #async for token in chatbot.process_input("default_user", user_input):
        #    yield token
    
    return StreamingResponse(
        response_stream(),
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
        media_type="text/event-stream"
    )


#no streaming
@app.post("/conversation-audio")
async def conversation_audio(audio: UploadFile):
    """
    End-to-end pipeline for audio-to-audio conversation.
    """
    try:
        # Step 1: Convert Speech to Text
        wav_audio = await convert_to_wav(audio)  
        stt_result = voice_to_text(wav_audio)
        if not stt_result["success"]:
            return JSONResponse(content={"error": stt_result["error"]}, status_code=400)

        user_input = stt_result["text"]
        print(f"User said: {user_input}")

        # Step 2: Generate Text Response
        response_text = ""
        async for chunk in chatbot.stream_workflow_response(user_input):
            response_text += chunk

        print(f"Generated response: {response_text}")

        # Ensure response_text is not empty
        if not response_text.strip():
            raise ValueError("No text to speak")
        
        # Generate speech using Coqui TTS
        output_filename = "response.wav"
        new_tts(response_text, filename=output_filename)

        # If needed, convert to MP3
        output_mp3_filename = "response.mp3"
        convert_wav_to_mp3(output_filename, output_mp3_filename)

        # Return the MP3 file
        return FileResponse(output_mp3_filename, media_type='audio/mpeg', filename=output_mp3_filename)

    except Exception as e:
        return JSONResponse(content={"error": f"Error in audio processing: {str(e)}"}, status_code=500)



cancel_event = asyncio.Event()

@app.post("/cancel")
async def cancel_stream():
    #global cancel_event
    cancel_event.set()  # Signal cancellation
    print("Cancel event triggered")
    return JSONResponse(content={"message": "Processing cancelled."}, status_code=200)


@app.post("/conversation-audio-stream")
async def conversation_audio_stream(audio: UploadFile, background_tasks: BackgroundTasks):
    cancel_event.clear()  # Reset the cancellation flag

    try:
        # Step 1: Convert Speech to Text
        wav_audio = await convert_to_wav(audio)
        stt_result = voice_to_text(wav_audio)
        if not stt_result["success"]:
            return JSONResponse(content={"error": stt_result["error"]}, status_code=400)
        
        user_input = stt_result["text"]
        print(f"User said: {user_input}")
        
        # Step 2: Generate Text Response
        response_text = ""
        async for chunk in chatbot.stream_workflow_response(user_input):
            if cancel_event.is_set():
                print("Processing cancelled")
                return
            response_text += chunk
        
        # Tokenize into sentences
        sentences = sent_tokenize(response_text)
        print(f"Generated sentences: {sentences}")
        
        # Stream individual WAV chunks with controlled chunk size
        async def generate_wav_chunks():
            if cancel_event.is_set():
                    print("Chunk generation cancelled")
                    return  # Stop chunk generation immediately if interrupted
            for sentence in sentences:
                if cancel_event.is_set():
                    print("Chunk generation cancelled")
                    return  # Stop chunk generation immediately if interrupted
                buffer = BytesIO()
                tts_model.tts_to_file(text=sentence, file_path=buffer)
                buffer.seek(0)
                chunk_data = buffer.read()
                max_chunk_size = 100 * 1024  # 100 KB

                for i in range(0, len(chunk_data), max_chunk_size):
                    if cancel_event.is_set():
                        print("Streaming cancelled during chunk generation")
                        return
                    chunk = chunk_data[i:i+max_chunk_size]
                    if i == 0:
                        print(f"First chunk includes header: {chunk[:4] == b'RIFF'}")
                    yield chunk
               
        # Return a streaming response with individual WAV chunks
        return StreamingResponse(generate_wav_chunks(), media_type="audio/wav")

    
    
    except Exception as e:    
        print(f"Error in audio processing: {str(e)}")
        import traceback
        traceback.print_exc()
        return JSONResponse(content={"error": f"Error in audio processing: {str(e)}"}, status_code=500)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
