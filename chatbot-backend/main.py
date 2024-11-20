from flask import Flask, request, jsonify, Response, stream_with_context
from flask_cors import CORS  # Import CORS
from transformers import BlenderbotTokenizer, BlenderbotForConditionalGeneration
from models.go_emotions import EmotionDetector
import json
import time

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Initialize model and tokenizer
tokenizer = BlenderbotTokenizer.from_pretrained("facebook/blenderbot-400M-distill")
model = BlenderbotForConditionalGeneration.from_pretrained("facebook/blenderbot-400M-distill")
goEmotions_detector = EmotionDetector()

# Function to generate a response using Blenderbot
def generate_response(user_input):
    try:
        # Generate the complete response first
        inputs = tokenizer(user_input, return_tensors='pt')
        response_ids = model.generate(**inputs)
        complete_response = tokenizer.batch_decode(response_ids, skip_special_tokens=True)[0]
        
         # Split the response into words
        words = complete_response.split()

         # Stream each word with a small delay
        accumulated_response = ""
        for i, word in enumerate(words):
            accumulated_response += word + " "
            # Get emotion analysis for the accumulated response
            emotion = goEmotions_detector.get_emotional_response(user_input, accumulated_response)
            
            # Create response object
            response_obj = {
                'response': accumulated_response.strip(),
                'emotion': emotion,
                'is_final': i == len(words) - 1
            }  

            yield json.dumps(response_obj) + '\n'
            time.sleep(0.1)  # Add a small delay between words

    except Exception as e:
        error_response = {
            'response': "I'm having trouble responding right now.",
            'emotion': None,
            'is_final': True,
            'error': str(e)
        }
        yield json.dumps(error_response) + '\n'


# Route to handle conversation
@app.route('/conversation', methods=['POST'])
def conversation():
    user_input = request.json.get('message')
    
    return Response(
        stream_with_context(generate_response(user_input)),
        mimetype='text/event-stream'
    )

if __name__ == '__main__':
    app.run(debug=True)
