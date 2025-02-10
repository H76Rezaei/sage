from transformers import LlamaForCausalLM, PreTrainedTokenizerFast, StoppingCriteria, StoppingCriteriaList
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

        # Initialize stop sequences
        self.user_stop_sequence = "User:"
        self.assistant_stop_sequence = "Assistant:"
        self.user_stop_token_ids = self.tokenizer.encode(self.user_stop_sequence, add_special_tokens=False)
        self.assistant_stop_token_ids = self.tokenizer.encode(self.assistant_stop_sequence, add_special_tokens=False)
        self.stop_sequences = [self.user_stop_token_ids, self.assistant_stop_token_ids]
        
        
    
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
    

    def generate_response(self, user_input: str) -> str:
        try:
            prompt_text = self._format_prompt(user_input)
            inputs = self.tokenizer(prompt_text, return_tensors="pt", add_special_tokens=True).to(self.device)

            # Create stopping criteria
            stopping_criteria = StoppingCriteriaList([self.MultiTokenStoppingCriteria(self.stop_sequences)])

            # Generate response with stopping criteria
            response_ids = self.model.generate(
                **inputs,
                max_new_tokens=self.max_tokens,
                temperature=self.temperature,
                top_p=self.top_p,
                do_sample=True,
                pad_token_id=self.tokenizer.eos_token_id,
                eos_token_id=self.tokenizer.eos_token_id,
                stopping_criteria=stopping_criteria,
            )

            # Decode and clean response
            full_response = self.tokenizer.decode(response_ids[0], skip_special_tokens=True)
            # Extract the Assistant's response, stopping at any User: or Assistant: parts
            assistant_response = full_response.split("Assistant:", 1)[-1]
            assistant_response = assistant_response.split("User:", 1)[0].split("Assistant:", 1)[0].strip()
            return assistant_response

        except Exception as e:
            print(f"Error generating response: {e}")
            return "I'm having trouble responding right now."
            
    

    async def generate_response_streaming(self, user_input):
        try:
            prompt_text = self._format_prompt(user_input)
            inputs = self.tokenizer(prompt_text, return_tensors="pt", add_special_tokens=True).to(self.device)

            generated_token_ids = []
            accumulated_text = ""
            current_input_ids = inputs["input_ids"]
            current_attention_mask = inputs["attention_mask"]

            while len(accumulated_text.split()) < self.max_tokens:
                with torch.no_grad():
                    outputs = self.model.generate(
                        input_ids=current_input_ids,
                        attention_mask=current_attention_mask,
                        max_new_tokens=1,
                        temperature=self.temperature,
                        top_p=self.top_p,
                        do_sample=True,
                        pad_token_id=self.tokenizer.eos_token_id,
                        eos_token_id=self.tokenizer.eos_token_id,
                    )

                    new_tokens = outputs[0][current_input_ids.shape[1]:]
                    new_tokens_list = new_tokens.tolist()
                    generated_token_ids.extend(new_tokens_list)

                    # Check for stop sequences
                    stop_generation = False
                    for seq in self.stop_sequences:
                        seq_len = len(seq)
                        if len(generated_token_ids) >= seq_len and generated_token_ids[-seq_len:] == seq:
                            generated_token_ids = generated_token_ids[:-seq_len]  # Remove the stop sequence
                            stop_generation = True
                            break
                    # Check for EOS
                    if self.tokenizer.eos_token_id in new_tokens_list:
                        stop_generation = True

                    if stop_generation:
                        new_text = self.tokenizer.decode(generated_token_ids, skip_special_tokens=True)
                        accumulated_text += new_text
                        break

                    # Decode and accumulate
                    new_text = self.tokenizer.decode(new_tokens, skip_special_tokens=True)
                    accumulated_text += new_text
                    yield new_text, False

                    # Update context
                    current_input_ids = torch.cat([current_input_ids, new_tokens.unsqueeze(0)], dim=1)
                    current_attention_mask = torch.cat(
                        [current_attention_mask, torch.ones_like(new_tokens.unsqueeze(0))], dim=1
                    )

            # Post-process to remove any stop sequences from the final accumulated text
            assistant_response = accumulated_text.split("User:", 1)[0].split("Assistant:", 1)[0].strip()
            yield assistant_response, True

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
        formatted_prompt += f"User: {user_input.strip()}\nProvide a single answer. Stop immediately after finishing Assistant response.\nAssistant:"
        return formatted_prompt
    

    class MultiTokenStoppingCriteria(StoppingCriteria):
        def __init__(self, stop_sequences):
            self.stop_sequences = stop_sequences

        def __call__(self, input_ids: torch.LongTensor, scores: torch.FloatTensor, **kwargs) -> bool:
            for seq in self.stop_sequences:
                seq_len = len(seq)
                if input_ids.size(1) >= seq_len:
                    current_segment = input_ids[0, -seq_len:].tolist()
                    if current_segment == seq:
                        return True
            return False