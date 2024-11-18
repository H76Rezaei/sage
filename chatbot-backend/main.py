from flask import Flask, request, jsonify, render_template
from flask_cors import CORS  # Import CORS
import nltk
from nltk.sentiment import SentimentIntensityAnalyzer
from transformers import BlenderbotTokenizer, BlenderbotForConditionalGeneration

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Initialize model and tokenizer
tokenizer = BlenderbotTokenizer.from_pretrained("facebook/blenderbot-400M-distill")
model = BlenderbotForConditionalGeneration.from_pretrained("facebook/blenderbot-400M-distill")

nltk.download('vader_lexicon')

# Function to generate a response using Blenderbot
def generate_response(user_input):
    try:
        inputs = tokenizer(user_input, return_tensors='pt')
        response_id = model.generate(**inputs)
        response = tokenizer.batch_decode(response_id, skip_special_tokens=True)[0]
        return response
    except Exception as e:
        print(f"Error generating response: {e}")
        return "I'm having trouble responding right now."

# Function to detect emotion
def detect_emotion(text):
    sia = SentimentIntensityAnalyzer()
    sentiment_scores = sia.polarity_scores(text)
    if sentiment_scores['compound'] >= 0.05:
        return "Positive"
    elif sentiment_scores['compound'] <= -0.05:
        return "Negative"
    else:
        return "Neutral"

# Route to handle conversation
@app.route('/conversation', methods=['POST'])
def conversation():
    user_input = request.json.get('message')
    response = generate_response(user_input)
    emotion = detect_emotion(user_input)
    return jsonify({'response': response, 'emotion': emotion})

if __name__ == '__main__':
    app.run(debug=True)
