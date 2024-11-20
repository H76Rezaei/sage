from flask import Flask, request, Response, stream_with_context
from flask_cors import CORS
from transformers import LlamaForCausalLM, PreTrainedTokenizerFast
from models.go_emotions import EmotionDetector
import json
import time


app = Flask(__name__)
CORS(app)

# Initialize Llama tokenizer and model
tokenizer = PreTrainedTokenizerFast.from_pretrained("meta-llama/Llama-3.2-1B-Instruct")
model = LlamaForCausalLM.from_pretrained("meta-llama/Llama-3.2-1B-Instruct")
goEmotions_detector = EmotionDetector()

# Function to generate response using Llama
def generate_response(user_input):
    try:
        # Tokenize input and generate a response
        inputs = tokenizer(user_input, return_tensors="pt")
        response_ids = model.generate(
            **inputs,
            max_new_tokens=500,
            temperature=0.5,
            top_p=0.7,
            do_sample=True
        )
        complete_response = tokenizer.decode(response_ids[0], skip_special_tokens=True)

        # Stream the response word by word
        words = complete_response.split()
        accumulated_response = ""
        for i, word in enumerate(words):
            accumulated_response += word + " "
            
            # Generate emotion analysis if necessary
            emotion = goEmotions_detector.get_emotional_response(user_input, accumulated_response)

            # Create response object
            response_obj = {
                "response": accumulated_response.strip(),
                "is_final": i == len(words) - 1
            }

            yield json.dumps(response_obj) + '\n'
            time.sleep(0.1)  # Simulate streaming delay

    except Exception as e:
        error_response = {
            "response": "I'm having trouble responding right now.",
            "is_final": True,
            "error": str(e)
        }
        yield json.dumps(error_response) + '\n'


# Route to handle conversation
@app.route('/conversation', methods=['POST'])
def conversation():
    user_input = request.json.get("message")
    
    return Response(
        stream_with_context(generate_response(user_input)),
        mimetype="text/event-stream"
    )

if __name__ == "__main__":
    app.run(debug=True)
