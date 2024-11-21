import json
import torch
import asyncio
from llama.model_manager import get_model_and_tokenizer
from llama.prompt_manager import get_initial_prompts

#checking my gpu
print(torch.cuda.is_available())  # Should return True
print(torch.cuda.get_device_name(0))  # Should show GPU name

# Always start with the initial prompt
initial_prompts = get_initial_prompts()

async def stream_generation(user_input, tokenizer, model):

    # Format the input as a single conversation with initial prompts
    prompt_text = "\n".join([f"{msg['role']}: {msg['content']}" for msg in initial_prompts])
    prompt_text += f"\nUser: {user_input}\nAssistant:"

    # Tokenize input
    inputs = tokenizer(
        prompt_text, 
        return_tensors="pt", 
        add_special_tokens=True
        ).to("cuda")
    
   
    #initialize generation parameters
    max_new_tokens = 200
    accumulated_text = ""

    #set up generation config
    generation_config = {
        "max_new_tokens": 1,
        "temperature": 0.7,
        "top_p": 0.9,
        "do_sample": True,
        "return_dict_in_generate": True,
        "num_return_sequences": 1,
        "pad_token_id": tokenizer.eos_token_id,
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
    

                 # Decode the generated tokens
                generated_sequence = outputs.sequences[0]

                # Decode only the new tokens
                new_tokens = generated_sequence[current_input_ids.shape[1]:].cpu()
                new_text = tokenizer.decode(new_tokens, skip_special_tokens=True)
                
                # Skip if no new text was generated
                if not new_text.strip():
                    break
                
                # Update accumulated text
                accumulated_text += new_text

                bot_response = accumulated_text.strip()

                # Clean up the response
                bot_response = bot_response.split("User:", 1)[0].strip()
                bot_response = bot_response.split("Assistant:", 1)[0].strip()

                # Create response object
                response_obj = {
                    "response": bot_response.strip(),
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
        "response": bot_response.strip(),
        "is_final": True,
    }
    yield f"data: {json.dumps(final_response)}\n\n"
    

