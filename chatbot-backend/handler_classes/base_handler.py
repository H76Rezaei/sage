from emotion_detection.go_emotions import EmotionDetector

class ModelHandlerBase:
    """
    Base class for all model handlers.
    """
    def __init__(self, parameters):
        
        """
        Initialize the model handler with provided parameters.
        """
        
        ## Common attributes
        self.model_name = parameters.get("model_name")  
        self.temperature = parameters.get("temperature")
        self.top_p = parameters.get("top_p")
        self.max_tokens = parameters.get("max_tokens")
        self.memory = parameters.get("memory")    ## True or false
        self.device = parameters.get("hardware")  ## cpu or gpu
        
        # Prompts
        self.system_prompt = parameters.get("system_prompt")     # string
        self.emotion_prompts = parameters.get("emotion_prompts")  # dictionary
        
        # Initialize emotion detector if emotion prompts exist
        self.emotion_detector = self.initialize_emotion_detector() if self.emotion_prompts else None
        
    
       
    def initialize_emotion_detector(self):
        """
        Initialize and return the emotion detector instance.
        """
        return EmotionDetector() # create and return an instance of the detector
    
    
    def detect_emotion_tag(self, user_input):
        """
        Detect the primary emotion from the user input and return it as a tag.
        """
        if not self.emotion_detector:
            print("Emotion detector is not initialized.")
            return None
        else:
            emotion_data = self.emotion_detector.detect_emotion(user_input)   ## detect emotion
        
            return emotion_data["primary_emotion"]   # return the primary emotion tag
        