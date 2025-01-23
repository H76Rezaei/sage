from fastapi import FastAPI, Request, BackgroundTasks, UploadFile
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import json
from companion.digital_companion import DigitalCompanion
from audio.audio_utils import (
    conversation_audio, 
    conversation_audio_stream, 
    cancel_stream
)

chatbot = DigitalCompanion()

app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/conversation")
async def conversation(request: Request):
    body = await request.json()
    user_input = body.get("message")
    
    async def response_stream():
        async for token in chatbot.stream_workflow_response(user_input):
            yield f"data: {json.dumps({'response': token, 'is_final': False})}\n\n"
        yield f"data: {json.dumps({'response': '', 'is_final': True})}\n\n"
    
    return StreamingResponse(
        response_stream(),
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
        media_type="text/event-stream"
    )

@app.post("/conversation-audio")
async def handle_conversation_audio(audio: UploadFile):
    return await conversation_audio(audio, chatbot)

@app.post("/cancel")
async def handle_cancel_stream():
    return await cancel_stream()

@app.post("/conversation-audio-stream")
async def handle_conversation_audio_stream(audio: UploadFile, background_tasks: BackgroundTasks):
    return await conversation_audio_stream(audio, background_tasks, chatbot)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)