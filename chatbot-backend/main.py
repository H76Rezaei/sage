from flask import Flask, request, Response, stream_with_context
from flask_cors import CORS
from transformers import LlamaForCausalLM, PreTrainedTokenizerFast
from models.go_emotions import EmotionDetector
import json
import torch

app = Flask(__name__)
CORS(app)

# Initialize Llama tokenizer and model
tokenizer = PreTrainedTokenizerFast.from_pretrained("meta-llama/Llama-3.2-1B-Instruct")
model = LlamaForCausalLM.from_pretrained("meta-llama/Llama-3.2-1B-Instruct")

# Set up the pad token
tokenizer.pad_token = tokenizer.eos_token
model.config.pad_token_id = tokenizer.pad_token_id

# Move model to GPU if available
if torch.cuda.is_available():
    model = model.cuda()
model.eval()  # Set to evaluation mode

goEmotions_detector = EmotionDetector()

def stream_generation(user_input):
    try:
        # Tokenize input
        inputs = tokenizer(
            user_input,
            return_tensors="pt",
            add_special_tokens=True
        )

        #continuation of GPU setup
        if torch.cuda.is_available():
            inputs = {k: v.cuda() for k, v in inputs.items()}
        
        # Initialize generation parameters
        max_new_tokens = 100
        accumulated_text = ""
        
        # Set up generation config
        generation_config = {
            "max_new_tokens": 10,
            "temperature": 0.5,
            "top_p": 0.9,
            "do_sample": True,
            "pad_token_id": tokenizer.pad_token_id,
            "return_dict_in_generate": True,
            "output_scores": False,
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
                new_tokens = generated_sequence[current_input_ids.shape[1]:]
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
                
                yield json.dumps(response_obj) + '\n'
                
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
        yield json.dumps(final_response) + '\n'

    except Exception as e:
        error_response = {
            "response": f"I'm having trouble responding right now. Error: {str(e)}",
            "is_final": True,
            "error": str(e)
        }
        yield json.dumps(error_response) + '\n'

@app.route('/conversation', methods=['POST'])
def conversation():
    user_input = request.json.get("message")
    return Response(
        stream_with_context(stream_generation(user_input)),
        mimetype="text/event-stream"
    )

if __name__ == "__main__":
    app.run(debug=True)