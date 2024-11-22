from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
import json
from llama.generation import stream_generation
from llama.model_manager import get_model_and_tokenizer
from llama.prompt_manager import get_initial_prompts
from fastapi import FastAPI, Request, UploadFile
from fastapi.responses import StreamingResponse, JSONResponse
from speech import  voice_to_text , text_to_speech


#llama model and tokenizer
model, tokenizer = get_model_and_tokenizer()

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

    return StreamingResponse(
        stream_generation(user_input, tokenizer, model),
        media_type="text/event-stream"
    )

@app.post("/voice-to-text")
async def voice_to_text_endpoint(audio: UploadFile):
    """
    Endpoint to convert speech to text.
    """
    result = voice_to_text(audio)
    if result["success"]:
        return JSONResponse(content={"text": result["text"]})
    else:
        return JSONResponse(content={"error": result["error"]}, status_code=400)
    
@app.post("/text-to-speech")
async def text_to_speech_endpoint(request: Request):
    """
    Endpoint to convert text to speech.
    """
    data = await request.json()
    text = data.get("text")
    if not text:
        return JSONResponse(content={"error": "Text cannot be empty"}, status_code=400)

    try:
        text_to_speech(text)
        return JSONResponse(content={"message": "Text converted to speech successfully"})
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)