import json
import torch
import asyncio
from llama.model_manager import get_model_and_tokenizer
from llama.prompt_manager import get_initial_prompts

def check_cuda_availability():
    """
    Check CUDA availability and return the appropriate device.
    
    Returns:
        torch.device: 'cuda' if available, otherwise 'cpu'
    """
    if torch.cuda.is_available():
        print(f"Using GPU: {torch.cuda.get_device_name(0)}")
        return torch.device('cuda')
    else:
        print("No GPU available. Falling back to CPU.")
        return torch.device('cpu')

async def generate_response(user_input, tokenizer, model):
    """
    Generate response tokens using the model.
    
    Returns:
        Iterator yielding generated text chunks
    """
    try:
        device = check_cuda_availability()
        
        # Format the input
        initial_prompts = get_initial_prompts()
        prompt_text = "\n".join([f"{msg['role']}: {msg['content']}" for msg in initial_prompts])
        prompt_text += f"\nUser: {user_input}\nAssistant:"

        # Tokenize input
        inputs = tokenizer(
            prompt_text, 
            return_tensors="pt", 
            add_special_tokens=True
        ).to(device)

        # Initialize parameters
        max_new_tokens = 500
        accumulated_text = ""
        
        generation_config = {
            "max_new_tokens": 1,
            "temperature": 0.5,
            "top_p": 0.7,
            "do_sample": True,
            "return_dict_in_generate": True,
            "num_return_sequences": 1,
            "pad_token_id": tokenizer.eos_token_id,
            "output_scores": False
        }

        # Move model to device
        model = model.to(device)
        
        # Keep track of context
        current_input_ids = inputs.input_ids
        current_attention_mask = inputs.attention_mask

        while len(accumulated_text.split()) < max_new_tokens:
            with torch.no_grad():
                outputs = model.generate(
                    input_ids=current_input_ids,
                    attention_mask=current_attention_mask,
                    **generation_config
                )

                # Decode new tokens
                generated_sequence = outputs.sequences[0]
                new_tokens = generated_sequence[current_input_ids.shape[1]:].cpu()
                new_text = tokenizer.decode(new_tokens, skip_special_tokens=True)
                
                if not new_text.strip():
                    break
                
                accumulated_text += new_text
                bot_response = accumulated_text.strip()
                
                # Clean up response
                bot_response = bot_response.split("User:", 1)[0].strip()
                bot_response = bot_response.split("Assistant:", 1)[0].strip()
                
                yield bot_response.strip(), tokenizer.eos_token_id in new_tokens
                
                # Update context
                current_input_ids = generated_sequence.unsqueeze(0).to(device)
                current_attention_mask = torch.ones_like(current_input_ids)
                
                if tokenizer.eos_token_id in new_tokens:
                    break

    except Exception as e:
        yield f"I'm having trouble responding right now. Error: {str(e)}", True

async def stream_generation(user_input, tokenizer, model):
    """
    Stream the generated response in a format suitable for SSE.
    """
    try:
        async for response_text, is_final in generate_response(user_input, tokenizer, model):
            response_obj = {
                "response": response_text,
                "is_final": is_final
            }
            yield f"data: {json.dumps(response_obj)}\n\n"
            
            if not is_final:
                await asyncio.sleep(0.1)
                
    except Exception as e:
        error_response = {
            "response": f"I'm having trouble responding right now. Error: {str(e)}",
            "is_final": True,
            "error": str(e)
        }
        yield f"data: {json.dumps(error_response)}\n\n"