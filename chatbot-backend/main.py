from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from transformers import LlamaForCausalLM, PreTrainedTokenizerFast, AutoModelForCausalLM
from models.go_emotions import EmotionDetector
import json
import torch
import asyncio


print(torch.cuda.is_available())  # Should return True
print(torch.cuda.get_device_name(0))  # Should show your GPU name


app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Initialize Llama tokenizer and model
model = LlamaForCausalLM.from_pretrained("meta-llama/Llama-3.2-1B-Instruct").to("cuda")
tokenizer = PreTrainedTokenizerFast.from_pretrained("meta-llama/Llama-3.2-1B-Instruct")

# Set up the pad token
tokenizer.pad_token = tokenizer.eos_token
model.config.pad_token_id = tokenizer.pad_token_id

goEmotions_detector = EmotionDetector()

async def stream_generation(user_input):
    try:
        # Tokenize input
        inputs = tokenizer(
            user_input,
            return_tensors="pt",
            add_special_tokens=True
        ).to("cuda")  # Move inputs to GPU
        
        # Initialize generation parameters
        max_new_tokens = 100
        accumulated_text = ""
        
        # Set up generation config
        generation_config = {
            "max_new_tokens": 10,  # Increase token generation
            "temperature": 0.7,
            "top_p": 0.9,
            "do_sample": True,
            "return_dict_in_generate": True,
            "output_scores": False
        }


        # Keep track of the current context
        current_input_ids = inputs.input_ids
        current_attention_mask = inputs.attention_mask
        
        while len(accumulated_text.split()) < max_new_tokens:
            with torch.no_grad():
                outputs = model.generate(
                    input_ids=current_input_ids,
                    attention_mask=current_attention_mask,
                    **generation_config
                )

                
                # Get the generated sequence
                generated_sequence = outputs.sequences[0]
                
                # Decode only the new tokens
                new_tokens = generated_sequence[current_input_ids.shape[1]:].cpu()
                new_text = tokenizer.decode(new_tokens, skip_special_tokens=True)
                
                # Skip if no new text was generated
                if not new_text.strip():
                    break
                
                # Update accumulated text
                accumulated_text += new_text
                
                # Create response object
                response_obj = {
                    "response": accumulated_text.strip(),
                    "is_final": False,
                }
                
                yield f"data: {json.dumps(response_obj)}\n\n"
                
                # Small delay to simulate streaming
                await asyncio.sleep(0.1)
                
                # Update context for next iteration
                current_input_ids = generated_sequence.unsqueeze(0)
                current_attention_mask = torch.ones_like(current_input_ids)
                
                # Check if we've hit the EOS token
                if tokenizer.eos_token_id in new_tokens:
                    break
        
        # Send final response
        final_response = {
            "response": accumulated_text.strip(),
            "is_final": True,
        }
        yield f"data: {json.dumps(final_response)}\n\n"

    except Exception as e:
        error_response = {
            "response": f"I'm having trouble responding right now. Error: {str(e)}",
            "is_final": True,
            "error": str(e)
        }
        yield f"data: {json.dumps(error_response)}\n\n"

@app.post("/conversation")
async def conversation(request: Request):
    body = await request.json()
    user_input = body.get("message")
    
    return StreamingResponse(
        stream_generation(user_input),
        media_type="text/event-stream"
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)