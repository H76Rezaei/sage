from transformers import LlamaForCausalLM, PreTrainedTokenizerFast
from handler_classes.base_handler import ModelHandlerBase
import torch

class LlamaCloudHandler(ModelHandlerBase):
    """
    Handler for the Llama Cloud model  with support for streaming and non-streaming responses.
    """
    
    def __init__(self, parameters: dict):
        super().__init__(parameters)
        
        ## Initialize Llama model and tokenizer
        print("Initializing Llama model and tokenizer...")
        self.model, self.tokenizer = self._initialize_model_and_tokenizer()
        self.model.to(self.device)
        
        
    
    def _initialize_model_and_tokenizer(self)->tuple:
        """
        Load the Llama model and tokenizer.
        """
        model = LlamaForCausalLM.from_pretrained(self.model_name)
        tokenizer = PreTrainedTokenizerFast.from_pretrained(self.model_name)
        
        # Set up the pad token
        #tokenizer.pad_token = tokenizer.eos_token
        #model.config.pad_token_id = tokenizer.pad_token_id
        
        # Add a distinct padding token to avoid conflicts with the eos token
        tokenizer.add_special_tokens({"pad_token": "<|reserved_special_token_0|>"})
        model.config.pad_token_id = tokenizer.pad_token_id
        tokenizer.padding_side = 'right'

        # Ensure EOS token is also set if needed
        if tokenizer.eos_token is None:
            tokenizer.eos_token = "<|end_of_text|>"
        if model.config.eos_token_id is None:
            model.config.eos_token_id = tokenizer.eos_token_id
        
        return model, tokenizer
    

    def generate_response(self, user_input:str)->str:
        """
        Generate a non-streaming response.
        """
        try:
            # Format the input prompt
            prompt_text = self._format_prompt(user_input)
            

            # Tokenize the input
            inputs = self.tokenizer(prompt_text, return_tensors="pt", add_special_tokens=True).to(self.device)

            # Generate response
            with torch.no_grad():
                response_ids = self.model.generate(
                    **inputs,
                    max_new_tokens=self.max_tokens,
                    temperature=self.temperature,
                    top_p=self.top_p,
                    do_sample=True,
                    pad_token_id=self.tokenizer.eos_token_id,
                    eos_token_id=self.tokenizer.eos_token_id,
                )

                # Decode and clean response
                response = self.tokenizer.decode(response_ids[0], skip_special_tokens=True).split("Assistant:", 1)[-1].strip()

                return response

        except Exception as e:
            print(f"Error generating response: {e}")
            return "I'm having trouble responding right now."
            
    

    async def generate_response_streaming(self, user_input):
        """
        Generate a streaming response.
        """
        try:
            # Format the input prompt
            prompt_text = self._format_prompt(user_input)
            
            # Tokenize the input
            inputs = self.tokenizer(
                prompt_text,
                return_tensors="pt",
                add_special_tokens=True
            ).to(self.device)
            
            # Initialize accumulated text
            accumulated_text = ""
            
            # Configuration for generation
            generation_config = {
                "temperature": self.temperature,
                "top_p": self.top_p,
                "max_new_tokens": 1,  # Generate one token at a time
                "do_sample": True,
                "pad_token_id": self.tokenizer.pad_token_id,
                "eos_token_id": self.tokenizer.eos_token_id,
                "output_scores": False
            }
            
            # Track context
            current_input_ids = inputs["input_ids"]
            current_attention_mask = inputs["attention_mask"]
            
            while len(accumulated_text.split()) < self.max_tokens:
                with torch.no_grad():
                    outputs = self.model.generate(
                        input_ids=current_input_ids,
                        attention_mask=current_attention_mask,
                        **generation_config
                    )
                    
                    # Extract newly generated tokens
                    new_tokens = outputs[0][current_input_ids.shape[1]:]
                    
                    # Decode new tokens
                    new_text = self.tokenizer.decode(new_tokens, skip_special_tokens=True)
                    
                    if new_text.strip():
                        accumulated_text += new_text
                        yield new_text, False  # Emit partial response
                    
                    # Check for end of sequence (eos_token)
                    if self.tokenizer.eos_token_id in new_tokens:
                        yield new_text.strip(), True  # Emit final response
                        break
                    
                    # Update context for next generation step
                    current_input_ids = torch.cat([current_input_ids, new_tokens.unsqueeze(0)], dim=1)
                    current_attention_mask = torch.cat(
                        [current_attention_mask, torch.ones_like(new_tokens.unsqueeze(0))], dim=1
                    )
            
        except Exception as e:
            yield f"Error: {str(e)}", True

    
    
    
    async def stream_generation(self, user_input):    ## it is for showing response in terminal- just for debugging purpose
        """
        Stream the generated response in the terminal.
        """
        full_response = ""
        try:
            async for token, is_final in self.generate_response_streaming(user_input):
                # Print the token and flush the output
                print(token, end="", flush=True)
                full_response += token
                #await asyncio.sleep(0.1)  # Simulate delay for natural flow

                if is_final:  # Stop if the EOS token is reached
                    break
            
            print("\nFull Response:", full_response.strip())
            print()  # Add a new line at the end of the response

        except Exception as e:
            print(f"Error during streaming: {str(e)}")
            
            
    
    def _format_prompt(self, user_input):
        """
        Format the input prompt manually, including optional emotion guidance.
        """
        # Start with the system prompt
        formatted_prompt = f"System: {self.system_prompt.strip()}\n" if self.system_prompt else ""

        # Add emotion guidance if available
        if self.emotion_detector:
            emotion_tag = self.detect_emotion_tag(user_input)
            emotion_prompt = self.emotion_prompts.get(emotion_tag, "")
            formatted_prompt += f"Emotion Guidance: {emotion_prompt.strip()}\n"

        # Add user input and ensure Assistant's response is marked clearly
        formatted_prompt += f"User: {user_input.strip()}\n Provide a single answer. Stop immediately after finishing Assistant response. \nAssistant:"
        return formatted_prompt