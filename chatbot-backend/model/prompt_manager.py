import logging
from typing import List
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import AIMessage, HumanMessage



class PromptManager:
    
    def __init__(self, system_prompt: str, max_context_tokens: int = 128_000):
        """
        Initializes the PromptManager.

        Args:
            system_prompt (str): The base system prompt template.
            emotion_prompts (dict): A dictionary mapping emotions to specific prompts.
            max_context_tokens (int): Maximum allowed tokens for the prompt.
        """
        self.prompt_template = self.create_prompt_template(system_prompt)
        self.max_context_tokens = max_context_tokens


    def create_prompt_template(self, system_prompt) -> ChatPromptTemplate:
        """
        Creates a formatted ChatPromptTemplate using the system prompt and placeholders.
        """
        return ChatPromptTemplate.from_messages(
            [
                (
                    "system", f"""{system_prompt}\n\n
                    ## Recall Memories\n
                    Recall memories are contextually retrieved based on the current 
                    conversation:\n{{recall_memories}}\n\n
                    ## Emotional Guidance\n
                    The user's emotion has been detected as '{{detected_emotion}}' based on their input.
                    {{emotion_prompt}}\n\n
                    """
                ),
                ("placeholder", "{messages}"),
            ]
        )

    def build_prompt_text(
        self, 
        detected_emotion: str, 
        emotion_guidance: str, 
        recall_memories: list[str], 
        stm_messages: list[AIMessage | HumanMessage]
    ) -> str:
        """
        Builds the final prompt text by filling placeholders in the system prompt.

        Args:
            detected_emotion (str): The detected emotion of the user.
            emotion_guidance (str): The emotion-specific prompt to guide the response.
            recall_memories (list[str]): List of retrieved memories relevant to the conversation.
            stm_messages (list[Union[AIMessage, HumanMessage]]): List of short-term memory (STM) messages.

        Returns:
            str: The fully constructed prompt text.
        """
        try:
            return self.prompt_template.format(
                recall_memories="\n".join(recall_memories),
                detected_emotion=detected_emotion,
                emotion_prompt=emotion_guidance,
                messages=stm_messages,
            )
        except KeyError as e:
            logging.error(f"Missing key in template placeholders: {e}")
            raise ValueError("Failed to build prompt") from e

    
    
    def calculate_total_tokens(self, 
                               detected_emotion: str, 
                               emotion_prompt: str, 
                               recall_memories: list[str], 
                               stm_messages: list[AIMessage, HumanMessage],
                               token_counter) -> int:
        """
        Calculates the total token usage for the constructed prompt.

        Args:
            detected_emotion (str): The detected emotion of the user.
            emotion_prompt (str): The emotion-specific prompt to guide the response.
            recall_memories (list[str]): List of retrieved memories relevant to the conversation.
            stm_messages (list[Union[AIMessage, HumanMessage]]): List of short-term memory (STM) messages.
            token_counter (callable): Function to calculate token count.

        Returns:
            int: Total token count of the constructed prompt.
        """
        prompt_text = self.build_prompt_text(
            detected_emotion=detected_emotion,
            emotion_prompt=emotion_prompt,
            recall_memories=recall_memories,
            stm_messages=stm_messages,
        )
        return token_counter(prompt_text)
    

############################################################################################################

    def str_token_counter(self, model, text: str) -> int:
        """
        Counts the number of tokens in a given text using the model's tokenizer.

        Args:
            text (str): The input text to be tokenized.

        Returns:
            int: The number of tokens in the input text.
        """
        token_ids = model.get_token_ids(text)
        
        return len(token_ids)
    
    ############################################################################################################    
    def calculate_total_tokens(self, 
                              model,
                              detected_emotion: str,
                              emotion_guidance: str,
                              recall_memories: List[str], 
                              stm_messages: List[HumanMessage | AIMessage]
                              ) -> int:
        """
        Calculates the total number of tokens for the generated prompt text.

        Args:
            detected_emotion (str): The detected emotion of the user.
            emotion_prompt (str): The emotion-specific prompt to guide the response.
            recall_memories (list[str]): List of retrieved memories relevant to the conversation.
            stm_messages (list[HumanMessage | AIMessage]): List of short-term memory (STM) messages.

        Returns:
            int: The total token count of the constructed prompt.
        """
        # Build the full prompt text
        prompt_text = self.build_prompt_text(detected_emotion, emotion_guidance, recall_memories, stm_messages) 
        
        # Count the number of tokens in the prompt text  
        num_tokens = self.str_token_counter(model, prompt_text)
        
        return num_tokens
    
    
    
    def validate_prompt_size(self, model, detected_emotion, emotion_guidance, recall_memories, stm_messages, max_tokens: int) -> bool:
        
        total_tokens = self.calculate_total_tokens(model, detected_emotion, emotion_guidance, recall_memories, stm_messages)
        if total_tokens > self.max_context_tokens - max_tokens:
            logging.error(f"Prompt exceeds token limit: {total_tokens} > {self.max_context_tokens - max_tokens}")
            return False
        
        return True