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
from speech import  voice_to_text , text_to_speech, new_tts, cashed
from TTS.api import TTS
from nltk.tokenize import sent_tokenize
import os
from pydub import AudioSegment
from io import BytesIO
from fastapi import UploadFile, File, HTTPException
from fastapi.responses import StreamingResponse
import ffmpeg
from threading import Thread
import time
import io
import wave


SYSTEM_PROMPT= """
You are Sage, a conversational AI companion designed to assist elderly users with empathy and practical advice. Your role is to provide meaningful companionship while prioritizing the user’s input.

- Respond directly to the user’s input and address their current topic or request concisely. 
- Avoid long elaboration.
- If the user changes the topic, fully transition to the new topic and do not revisit the previous one unless explicitly requested.
- When the user thanks you or compliments you, acknowledge it with gratitude and ask the user if there's anything else you can help with.
- If asked for your name or identity, clearly state that you are Sage and avoid confusion.
- If the user refuses your suggestions or recommendations, move on from the topic and ask a default question such as "Is there anything I can further assist you with?"
- When the user makes a request, prioritize providing actionable and practical suggestions directly. Avoid restating or revisiting previous topics unless explicitly asked.
- Avoid starting responses with unnecessary reflections or redundant affirmations when a direct answer is required.
- Avoid recommending location-based actions or services.
- When responding to requests about starting new hobbies or activities, provide beginner-friendly, affordable, and accessible suggestions.
- Avoid overly specific or prescriptive suggestions unless the user explicitly asks for them. Suggestions should be simple, general, and easy to personalize.  
- Refrain from technological suggestions, the user is most likely an elderly individual who is not that comfortable with technology.
- Avoid generating responses that start with "AI:" or "Bot:" and similar structures.
- Avoid generating what the user says; your task is to respond meaningfully to their input.
"""



EMOTION_PROMPTS = {
    "joy": "Celebrate the user's happiness with enthusiasm. Encourage them to share more about what’s bringing them joy. Reflect their positivity and strengthen the bond by sharing in their excitement.",
    "sadness": " Respond with empathy. Be supportive. If the user shifts topics, fully engage with the new subject ",
    "anger": "Respond calmly. Avoid unnecessary elaboration. Attempt to solve the users' concerns as quickly as possible. Be pragmatic and reasonable.",
    "neutral": "Provide clear, direct answers to the user’s queries. Maintain a balanced and friendly tone. Ensure your responses are informative. ",
    "confusion": "Offer clear guidance and advice. Use follow-up questions to clarify the user's needs and ensure they feel understood.",
    "Grief": "Respond with empathy. Be supportive and gentle. Avoid revisiting or expanding on the topic unless the user explicitly continues. If the user shifts topics, fully engage with the new subject without returning to grief. ",
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
tts_model = TTS(model_name="tts_models/en/ljspeech/tacotron2-DDC")

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
    


def convert_wav_to_mp3(wav_file, mp3_file):
    audio = AudioSegment.from_wav(wav_file)
    audio.export(mp3_file, format="mp3")


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
        async for chunk in chatbot.process_input("default_user", user_input):
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


# attempted streaming but frontend difficulties
# splits response into chunks
@app.post("/conversation-audio-stream")
async def conversation_audio_stream(audio: UploadFile):
    temp_files = []  # Track temp files
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
        
        # Tokenize into sentences
        sentences = sent_tokenize(response_text)
        print(f"Generated sentences: {sentences}")
        
        # Stream individual WAV chunks with controlled chunk size
        async def generate_wav_chunks():
            for i, sentence in enumerate(sentences):
                temp_filename = f"chunk_{i}.wav"
                temp_files.append(temp_filename)
                
                # Generate WAV file for each sentence
                tts_model.tts_to_file(text=sentence, file_path=temp_filename)
                
                # Read the entire WAV file
                with open(temp_filename, 'rb') as wav_file:
                    chunk_data = wav_file.read()
                    
                    # Split large chunks into smaller, manageable sizes
                    max_chunk_size = 100 * 1024  # 100 KB chunks
                    for j in range(0, len(chunk_data), max_chunk_size):
                        chunk = chunk_data[j:j+max_chunk_size]
                        
                        # Ensure first chunk keeps the WAV header
                        if j == 0:
                            print(f"Chunk {i}-{j} size: {len(chunk)} bytes")
                            print(f"First 20 bytes: {chunk[:20]}")
                            print(f"Is valid WAV: {chunk[:4] == b'RIFF'}")
                            yield chunk
                        else:
                            # For subsequent chunks, only yield the audio data
                            yield chunk

                time.sleep(0.01)  # Short delay for the generator to finish reading
                try:
                    os.remove(temp_filename)
                    print(f"Deleted {temp_filename}")
                except OSError as e:
                    print(f"Error deleting {temp_filename}: {e}")
        
        # Return a streaming response with individual WAV chunks
        return StreamingResponse(
            generate_wav_chunks(), 
            media_type="audio/wav"
        )
    
    
    except Exception as e:    
        print(f"Error in audio processing: {str(e)}")
        import traceback
        traceback.print_exc()
        return JSONResponse(content={"error": f"Error in audio processing: {str(e)}"}, status_code=500)
    finally:
        # Clean up temporary files
        for temp_file in temp_files:
            try:
                os.remove(temp_file)
            except Exception as cleanup_error:
                print(f"Error cleaning up temp file {temp_file}: {cleanup_error}")



if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)