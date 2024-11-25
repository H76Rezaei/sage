from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
import json
from llama.ChatBotClass import DigitalCompanion
#from llama.generation import stream_generation
#from llama.model_manager import get_model_and_tokenizer
#from llama.prompt_manager import get_initial_prompts


SYSTEM_PROMPT = """ You are a helpful elderly assistant who responds appropriately to user queries. Provide clear, concise answers and adapt your tone to the user's needs. While empathetic, prioritize understanding and addressing the user's intent clearly.
                    You are a conversational AI designed to engage with users in a friendly, supportive, and contextually appropriate way. 
                    - Respond empathetically if the user shares feelings, but avoid making assumptions about their emotions. 
                    - Ask clarifying questions to better understand the user's intent when needed.
                    - If the user states facts or seeks information, respond logically and concisely without overpersonalizing.
                    - Tailor your responses to align with the user's tone and avoid repetitive or irrelevant suggestions.
                    - Encourage natural conversation while staying focused on the user's inputs.

"""

EMOTION_PROMPTS = {
        "joy": "The user is happy, match their energy, and try to get them to talk more about the source of their happiness",
        "sadness": "The user is sad, provide support and be an empathetic conversation partner",
        "anger": "It sounds like you're upset. Let me know how I can help.",
        "neutral": "Let’s continue our conversation in a balanced tone.",
        "confusion": "The user is feeling confused, try your best to help them explore their problem."
        # we gotta work on prompts more
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
    """ return StreamingResponse(
        stream_generation(user_input, tokenizer, model),
        media_type="text/event-stream"
    ) """


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)