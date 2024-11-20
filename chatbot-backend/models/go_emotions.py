from transformers import AutoModelForSequenceClassification, AutoTokenizer
import torch
import numpy as np

class EmotionDetector:
    def __init__(self):
        self.model_name = "SamLowe/roberta-base-go_emotions"
        self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
        self.model = AutoModelForSequenceClassification.from_pretrained(self.model_name)
        
        # Map emotion indices to labels
        self.emotions = [
            'admiration', 'amusement', 'anger', 'annoyance', 'approval', 'caring',
            'confusion', 'curiosity', 'desire', 'disappointment', 'disapproval',
            'disgust', 'embarrassment', 'excitement', 'fear', 'gratitude', 'grief',
            'joy', 'love', 'nervousness', 'optimism', 'pride', 'realization',
            'relief', 'remorse', 'sadness', 'surprise', 'neutral'
        ]

    def detect_emotion(self, text):
        """
        Detect emotions in the given text using the RoBERTa model.
        Returns both the primary emotion and the full emotion distribution.
        """
        # Tokenize the text
        inputs = self.tokenizer(text, return_tensors="pt", truncation=True, max_length=512)
        
        # Get model predictions
        with torch.no_grad():
            outputs = self.model(**inputs)
            predictions = torch.nn.functional.softmax(outputs.logits, dim=-1)
            
        # Convert predictions to numpy for easier handling
        scores = predictions.numpy()[0]
        
        # Get the primary emotion (highest score)
        primary_emotion = self.emotions[np.argmax(scores)]
        
        # Create a dictionary of all emotions and their scores
        emotion_scores = {emotion: float(score) for emotion, score in zip(self.emotions, scores)}
        
        return {
            'primary_emotion': primary_emotion,
            'emotion_scores': emotion_scores
        }

    def get_emotional_response(self, text, response):
        """
        Analyze both the input text and response to provide emotional context
        """
        input_emotions = self.detect_emotion(text)
        response_emotions = self.detect_emotion(response)
        
        return {
            'input_analysis': input_emotions,
            'response_analysis': response_emotions
        }