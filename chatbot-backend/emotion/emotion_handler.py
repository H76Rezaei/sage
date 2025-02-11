import logging
from emotion.emotion_detection.go_emotions import EmotionDetector

class EmotionHandler:
    
    def __init__(self, emotion_prompts):
        """
        Processes emotions from user inputs and generates emotion-specific prompts.

        Args:
            emotion_detector: An instance of the emotion detection model.
            emotion_prompts (dict): A dictionary mapping emotions to specific prompts.
        """
        self.emotion_detector = EmotionDetector()
        self.emotion_prompts = emotion_prompts

    def detect_emotion_tag(self, user_input: str) -> str:
        """
        Detect the primary emotion from the user's input.

        Args:
            user_input (str): The input text from the user.

        Returns:
            str: The detected primary emotion.

        Raises:
            ValueError: If emotion detection fails or no primary emotion is found.
        """
        if not self.emotion_detector:
            raise ValueError("Emotion detector is not initialized.")

        try:
            emotion_data = self.emotion_detector.detect_emotion(user_input)
            #logging.info(f"Detected emotion data: {emotion_data}")
            return emotion_data["primary_emotion"]
        except Exception as e:
            logging.error(f"Error detecting emotion: {e}")
            return "neutral"

    def generate_emotion_prompt(self, user_input: str) -> str:
        """
        Generate an additional prompt based on the detected emotion.

        Args:
            user_input (str): The input text from the user.

        Returns:
            tuple[str, str]: The detected emotion and the corresponding emotion-specific prompt.
        """
        try:
            detected_emotion = self.detect_emotion_tag(user_input)
            emotion_guidance = self.emotion_prompts.get(detected_emotion, "")
            #logging.info(f"Generated prompt for emotion '{detected_emotion}': {emotion_guidance}")
            return detected_emotion, emotion_guidance
        except Exception as e:
            logging.error(f"Error generating emotion prompt: {e}")
            return ""



