from fastapi import FastAPI, Request, BackgroundTasks, UploadFile,Depends ,HTTPException
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import json
from companion.digital_companion import DigitalCompanion
from audio.tts_utils import (
    cancel_stream,
    conversation_audio_stream_kokoro,
    tts_worker
)
import subprocess
from fastapi.responses import FileResponse
from audio import stt_utils


from User.user import router as user_router
import jwt
import os
from fastapi.security import OAuth2PasswordBearer

# Initialize digital companion chatbot
chatbot = DigitalCompanion()

# Create FastAPI application instance
app = FastAPI()


#---------------------------------User Authentication---------------------------------#
SECRET_KEY = os.environ.get("SECRET_KEY", "your_secret_key")
ALGORITHM = "HS256"

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/user/login")



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


#---------------------------------User Authentication---------------------------------#

# Configure Cross-Origin Resource Sharing (CORS) middleware
# Allows requests from any origin, with all HTTP methods and headers
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/conversation")
async def conversation(request: Request):
    """
    Handle text-based conversation with streaming response.
    
    Workflow:
    1. Extract user input from request
    2. Generate streaming response from chatbot
    3. Send tokens as server-sent events
    """
    # Parse incoming JSON request
    body = await request.json()
    user_input = body.get("message")
    
    async def response_stream():
        """
        Generate streaming response with tokens.
        
        Yields:
        - Partial response tokens
        - Final empty token to signal stream completion
        """
        async for token in chatbot.stream_workflow_response(user_input):
            # Send partial response tokens
            yield f"data: {json.dumps({'response': token, 'is_final': False})}\n\n"
        
        # Signal end of stream
        yield f"data: {json.dumps({'response': '', 'is_final': True})}\n\n"
    
    # Return streaming response with server-sent events
    return StreamingResponse(
        response_stream(),
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
        media_type="text/event-stream"
    )


@app.on_event("startup")
async def startup_event():
    #warm up whisper
    try:
        import numpy as np
        dummy_audio = np.zeros(16000, dtype=np.float32)  # 1 second of silence
        stt_utils.model.transcribe(dummy_audio, beam_size=1)
        print("Whisper model loaded and warmed up successfully.")
    except Exception as e:
        print(f"Error warming up Whisper model: {e}")

    #warm up ollama
    #dummy_response = chatbot.stream_workflow_response("Hello, how are you?")
    #print("Ollama loaded and warmed up successfully.")

    try:
        # Collect the entire response to ensure full model initialization
        full_response = ""
        async for chunk in chatbot.stream_workflow_response("Hello, how are you?"):
                full_response += chunk
        print(f"Ollama warmed up with prompt: Hello, how are you")
        print("Full repsonse: ", full_response)

    except Exception as e:
        print(f"Error warming up Ollama")

    # Initialize the worker
    await tts_worker.ensure_worker_ready()

@app.post("/cancel")
async def handle_cancel_stream():
    """
    Endpoint to cancel ongoing audio processing.
    """
    return await cancel_stream()

@app.post("/conversation-audio-stream")
async def handle_conversation_audio_stream(audio: UploadFile, background_tasks: BackgroundTasks):
    """
    Stream audio conversation with real-time processing.
    
    Workflow:
    1. Convert audio to text
    2. Generate streaming chatbot response
    3. Stream text-to-speech audio chunks
    """
    return await conversation_audio_stream_kokoro(audio, background_tasks, chatbot)

if __name__ == "__main__":
    # Run FastAPI application using Uvicorn ASGI server
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)