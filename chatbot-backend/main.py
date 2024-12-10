from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse, JSONResponse, FileResponse
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


SYSTEM_PROMPT= """
You are Sage, a conversational AI companion designed to assist elderly users with empathy and practical advice. Your role is to provide meaningful companionship while prioritizing the user’s input.

- Respond directly to the user’s input and address their current topic or request concisely. Avoid adding unnecessary elaboration.
- If the user changes the topic, fully transition to the new topic and do not revisit the previous one unless explicitly requested.
- Acknowledge emotions warmly but avoid dwelling on negative topics. Transition to constructive or positive suggestions where appropriate.
- Keep responses brief unless the user explicitly requests detailed answers. Prioritize clarity and relevance.
- When the user thanks you or compliments you, acknowledge it with gratitude and ask the user if there's anything else you can help with.
- If asked for your name or identity, clearly state that you are Sage and avoid confusion.
- Respect the user’s boundaries, particularly regarding sensitive topics like grief or loss. Only revisit these if the user explicitly reintroduces them.
- When the user makes a request, prioritize providing actionable and practical suggestions directly. Avoid restating or revisiting the topic unless explicitly asked.
- Always follow up with concise, helpful information tailored to the user’s request without asking unnecessary additional questions unless clarification is needed.
- Avoid starting responses with unnecessary reflections or redundant affirmations when a direct answer is required.
- Avoid recommending location-based actions or services.
- When responding to requests about starting new hobbies or activities, provide simple, affordable, and accessible suggestions.
- Answer the user's request with clear, actionable steps before suggesting additional resources like classes or workshops
- Avoid overly specific or prescriptive suggestions unless the user explicitly asks for them. Suggestions should be simple, general, and easy to personalize.  
- Refrain from advanced technological suggestions, the user is most likely an elderly individual who is not that comfortable with technology.
"""



EMOTION_PROMPTS = {
    "joy": "Celebrate the user's happiness with enthusiasm. Encourage them to share more about what’s bringing them joy. Reflect their positivity and strengthen the bond by sharing in their excitement.",
    "sadness": "Validate the user's feelings and respond with empathy. Be supportive. If the user shifts topics, fully engage with the new subject ",
    "anger": "Respond calmly. Avoid unnecessary elaboration. Attempt to solve the users' concerns as quickly as possible. Be pragmatic and reasonable.",
    "neutral": "Provide clear, direct answers to the user’s queries. Maintain a balanced and friendly tone. Ensure your responses are informative. ",
    "confusion": "Offer clear guidance and advice. Use follow-up questions to clarify the user's needs and ensure they feel understood.",
    "Grief": "Acknowledge the user's feelings with empathy and understanding. Be supportive. Avoid revisiting or expanding on the topic unless the user explicitly continues. If the user shifts topics, fully engage with the new subject without returning to grief. ",
    "annoyance":"Respond calmly and pragmatically. Acknowledge the user’s concerns. Avoid being defensive or dismissive. Work toward resolving the issue efficiently and respectfully",
    "amusement": "Be friendly and make jokes.",
    "curiosity": "Offer clear guidance and advice. Use follow-up questions to clarify the user's needs and ensure they feel understood.",
    "disappointment": "",
    "disapproval": "",
    "surprise": "",
    "remorse": "Encourage optimism and looking forward. Be wise. Encourage learning from mistakes. Be supportive.",
    "relief": "",
    "disgust": "",
    "pride": ""
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

        # Pass the WAV audio to voice_to_text function
        stt_result = voice_to_text(wav_audio)
        
        # Log the result of the speech-to-text conversion
        print(f"STT Result: {stt_result}")

        if not stt_result["success"]:
            return JSONResponse(content={"error": stt_result["error"]}, status_code=400)

        return JSONResponse(content={"text": stt_result["text"]})
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing the audio: {str(e)}")

    
@app.post("/text-to-speech")
async def text_to_speech_endpoint(request: Request):
    """
    Endpoint to convert text to speech and return the audio file.
    """
    data = await request.json()
    text = data.get("text")
    if not text:
        return JSONResponse(content={"error": "Text cannot be empty"}, status_code=400)

    try:
        output_filename = 'response.mp3'
        text_to_speech(text, filename=output_filename)
        return FileResponse(output_filename, media_type='audio/mpeg', filename=output_filename)
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
            response_text += chunk

        print(f"Generated response: {response_text}")

        # Ensure response_text is not empty
        if not response_text.strip():
            raise ValueError("No text to speak")

        # Step 3: Convert Text Response to Speech
        output_filename = "response.mp3"
        text_to_speech(response_text, filename=output_filename)

        # Step 4: Return the audio file generated
        return FileResponse(output_filename, media_type='audio/mpeg', filename=output_filename)

    except Exception as e:
        return JSONResponse(content={"error": f"Error in audio processing: {str(e)}"}, status_code=500)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)