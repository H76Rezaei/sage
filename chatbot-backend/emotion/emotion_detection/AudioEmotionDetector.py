import torch
import numpy as np
from transformers import Wav2Vec2ForSequenceClassification, Wav2Vec2Processor
import librosa


class EmotionDetectorAudio:
    def __init__(self, max_length=32000):
        """
        Initialize the Emotion Detector for audio inputs.
        """
        # Set default paths if not provided
        model_path = 'C:/Users/asham/Desktop/Chat-bot/fine_tuned_model/fine_tuned_model'
        processor_path = 'C:/Users/asham/Desktop/Chat-bot/fine_tuned_processor/fine_tuned_processor'

        self.model_path = model_path 
        self.processor_path = processor_path 
        self.max_length = max_length

        # Load the model and processor
        self.model = Wav2Vec2ForSequenceClassification.from_pretrained(self.model_path)
        self.processor = Wav2Vec2Processor.from_pretrained(self.processor_path)

        # Define label mapping
        self.emotions = {
            0: 'neutral',
            1: 'angry',
            2: 'fear',
            3: 'sad',
            4: 'disgust',
            5: 'happy',
        }

    def load_and_process_audio(self, audio_path):
        """
        Load and process an audio file.
        """
        speech, sr = librosa.load(audio_path, sr=16000)
        inputs = self.processor(
            speech,
            sampling_rate=16000,
            return_tensors='pt',
            padding=True,
            truncation=True,
            max_length=self.max_length
        )
        return inputs['input_values']

    def detect_emotion(self, audio_path):
        """
        Detect emotions in the given audio file.
        """
        input_values = self.load_and_process_audio(audio_path)
        with torch.no_grad():
            logits = self.model(input_values).logits
            probabilities = torch.nn.functional.softmax(logits, dim=-1)
        
        # Convert predictions to numpy for easier handling
        scores = probabilities.numpy()[0]
        
        # Get the primary emotion (highest score)
        primary_emotion = self.emotions[np.argmax(scores)]
        
        # Create a dictionary of all emotions and their scores
        emotion_scores = {self.emotions[idx]: float(score) for idx, score in enumerate(scores)}
        
        return {
            'primary_emotion': primary_emotion,
            'emotion_scores': emotion_scores
        }