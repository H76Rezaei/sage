from transformers import BlenderbotTokenizer, BlenderbotForConditionalGeneration
from handler_classes.base_handler import ModelHandlerBase



class BlenderBotHandler(ModelHandlerBase):
    """
    Handler for BlenderBot-based conversation generation
    """
       
    def __init__(self, parameters: dict):
        super().__init__(parameters)
        
        try:
        
            ## Initialize Blenderbot model and tokenizer
            print("Initializing Blenderbot model and tokenizer...")
            self.tokenizer = BlenderbotTokenizer.from_pretrained(self.model_name)
            self.model = BlenderbotForConditionalGeneration.from_pretrained(self.model_name)
            
            self.model.to(self.device)
            
        except Exception as e:
            raise RuntimeError(f"Failed to initialize BlenderBotHandler: {e}")
        
        
    def generate_response(self, user_input: str) -> str:
        """
        Generate a response using the BlenderBot model.
        
        Args:
            user_input (str): User input text.
        
        Returns:
            str: The model's response to the user input.
        """
        try:
            ## Tokenize the user input
            inputs = self.tokenizer(user_input, return_tensors="pt").to(self.device)
            
            ## Generate response with parameters
            response_ids = self.model.generate(
                **inputs,
                max_length=self.max_tokens,
                temperature=self.temperature,
                top_p=self.top_p,
                )
            
            ## Decode the response
            response = self.tokenizer.batch_decode(response_ids, skip_special_tokens=True)[0]
            return response
        
        except Exception as e:
            print(f"Error generating response: {e}")
            return "I'm having trouble responding right now."