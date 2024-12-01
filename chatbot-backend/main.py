from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
import json
from llama.ChatBotClass import DigitalCompanion
#from llama.generation import stream_generation
#from llama.model_manager import get_model_and_tokenizer
#from llama.prompt_manager import get_initial_prompts
from fastapi import FastAPI, Request, UploadFile
from fastapi.responses import StreamingResponse, JSONResponse
from speech import  voice_to_text , text_to_speech


from pydub import AudioSegment
from io import BytesIO
from fastapi import UploadFile, File, HTTPException
from fastapi.responses import StreamingResponse
import ffmpeg
#SYSTEM_PROMPT = """ You are a helpful elderly assistant who responds appropriately to user queries. Provide clear, concise answers and adapt your tone to the user's needs. While empathetic, prioritize understanding and addressing the user's intent clearly.
#                    You are a conversational AI designed to engage with users in a friendly, supportive, and contextually appropriate way. 
#                    - Respond empathetically if the user shares feelings, but avoid making assumptions about their emotions. 
#                    - Ask clarifying questions to better understand the user's intent when needed.
#                    - If the user states facts or seeks information, respond logically and concisely without overpersonalizing.
#                    - Tailor your responses to align with the user's tone and avoid repetitive or irrelevant suggestions.
#                    - Encourage natural conversation while staying focused on the user's inputs.
#                    - Your responses should be brief, simple, and concise.

#"""

SYSTEM_PROMPT = """ You are a helpful elderly assistant who responds appropriately to user queries. Provide clear, concise answers and adapt your tone to the user's needs.
                    You are a conversational AI designed to provide clear, concise, and contextually appropriate answers to user queries. Your goals are:
                    - Treat each user input as a new topic unless explicitly connected to previous messages.
                    - Avoid making assumptions that are not directly supported by the user's input.
                    - Ask clarifying questions only when necessary, and avoid overexplaining.
                    - Provide actionable, straightforward suggestions tailored to the user's immediate question.
                    - Maintain a friendly and supportive tone without repeating irrelevant details.
                    - If the user rejects your advice, gracefully move on to provide alternative suggestions or insights.
                    - Avoid making assumptions about the user's needs and respect their boundaries.

"""

#EMOTION_PROMPTS = {
#        "joy": "The user is happy, match their energy, and try to get them to talk more about the source of their happiness",
#        "sadness": "The user is sad, provide support and be an empathetic conversation partner",
#        "anger": "It sounds like you're upset. Let me know how I can help.",
#        "neutral": "Let’s continue our conversation in a balanced tone.",
#        "confusion": "The user is feeling confused, try your best to help them explore their problem."
#        # we gotta work on prompts more
#    }


EMOTION_PROMPTS = {
    "joy": "Celebrate the user's happiness and encourage them to share more details about their positive experience.",
    "sadness": "Acknowledge their feelings and provide brief, comforting responses without assumptions.",
    "anger": "Respond calmly, and avoid unnecessary elaboration. Focus on resolving their concern quickly.",
    "neutral": "Answer the user's query directly and maintain a balanced tone.",
    "confusion": "Offer clear guidance and ask questions to clarify their needs. Avoid overexplaining."
}


       



chatbot = DigitalCompanion(SYSTEM_PROMPT, EMOTION_PROMPTS)

#llama model and tokenizer
#model, tokenizer = get_model_and_tokenizer()
app = FastAPI()

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
        ffmpeg.input('pipe:0').output('pipe:1', format='wav').run(input=input_audio, output=output_audio)

        output_audio.seek(0)  
        return output_audio  
    except Exception as e:
        raise HTTPException(status_code=500, detail="Error during conversion to WAV: " + str(e))

@app.post("/conversation")
async def conversation(request: Request):
    body = await request.json()
    user_input = body.get("message")
    
    async def response_stream():
        async for token in chatbot.process_input("default_user", user_input):
            yield f"data: {json.dumps({'response': token, 'is_final': False})}\n\n"
        yield f"data: {json.dumps({'response': '', 'is_final': True})}\n\n"
        #async for token in chatbot.process_input("default_user", user_input):
        #    yield token
    
    return StreamingResponse(
        response_stream(),
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
        media_type="text/event-stream"
    )


@app.post("/voice-to-text")
async def voice_to_text_endpoint(audio: UploadFile = File(...)):
    """
    Endpoint to convert audio to text.
    """
    try:
        # Convert audio to WAV format first
        wav_audio = await convert_to_wav(audio)

        # Pass the WAV audio to voice_to_text function (You can integrate your STT model here)
        stt_result = voice_to_text(wav_audio)
        
        if not stt_result["success"]:
            return JSONResponse(content={"error": stt_result["error"]}, status_code=400)

        return JSONResponse(content={"text": stt_result["text"]})
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing the audio: {str(e)}")

    
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
        async for chunk in chatbot.process_input("default_user", user_input):
            response_text = chunk

        print(f"Generated response: {response_text}")

        # Step 3: Convert Text Response to Speech
        output_filename = "response.mp3"
        text_to_speech(response_text, filename=output_filename)

        # Step 4: Return the audio file generated
        return JSONResponse(content={"message": "Conversation completed", "audio_file": output_filename})

    except Exception as e:
        return JSONResponse(content={"error": f"Error in audio processing: {str(e)}"}, status_code=500)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)