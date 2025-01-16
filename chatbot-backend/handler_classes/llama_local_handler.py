from langchain_community.chat_models import ChatOllama
from langchain_core.prompts import (
    ChatPromptTemplate,
    MessagesPlaceholder,
    SystemMessagePromptTemplate,
    HumanMessagePromptTemplate,
)
from langchain.chains import LLMChain
from langchain.memory import ConversationSummaryBufferMemory

from handler_classes.base_handler import ModelHandlerBase
import logging


class LlamaLocalHandler(ModelHandlerBase):
    """
    Handler for the Llama Local model with memory, emotion tagging, and streaming capabilities.
    """

    def __init__(self, parameters:dict):
        
        """
        Initialize the llama local handler.
        
        Args:
            parameters (dict): Configuration parameters for the model.
        """
        super().__init__(parameters)
        
        self.model = ChatOllama(
            model=self.model_name,
            temperature=self.temperature,
            top_p=self.top_p,
            max_tokens=self.max_tokens,
            device=self.device,
            stream=True)
        
        ## Initialize ChatPromptTemplate 
        self.prompt = ChatPromptTemplate(
            messages=[
                SystemMessagePromptTemplate.from_template(self.system_prompt),
                MessagesPlaceholder(variable_name="chat_history"),
                HumanMessagePromptTemplate.from_template("{user_input}"),
            ]
        )
        
        ## Initialize memory
        self.max_tokens_limit = parameters.get("max_tokens_limit_mem")
        self.max_history_length = parameters.get("max_history_length")
        self.sessions = {}
        
        
    def create_session(self, user_id:str) -> None:
        
        """
        Create a new session for a user.
        
        Args: user_id (str): The unique identifier for the user.
        """
        memory = ConversationSummaryBufferMemory(
        llm = self.model,
        memory_key="chat_history",
        return_messages=True,
        max_history_length=self.max_history_length,
        max_token_limit=self.max_tokens_limit
        )
        
        self.sessions[user_id] = {"memory": memory}
        logging.info(f"Session created for user {user_id}")    
        
    
    def get_session(self, user_id):
        """
        Retrieve an existing session for a user.
        
        Args: 
            user_id (str): The unique identifier for the user.
        
        Returns:   
            dict: The session information.
        """
            
        if user_id not in self.sessions:
            raise ValueError(f"No session found for user {user_id}")
            
        return self.sessions[user_id]
    
        
    async def generate_response_streaming(self, user_id, user_input): ### previous name: process_input
        
            """
            Stream the response token by token using llm.astream.
            
            Args:
                user_id (str): The unique identifier for the user.
                user_input (str): User input text .
            
            Yields:
                str: Streamed response token.
            """
            
            if user_id not in self.sessions:
                self.create_session(user_id)

            memory = self.sessions[user_id]["memory"]

            # Step 1: Generate emotion-specific guidance
            emotion_guidance = self.generate_emotion_prompt(user_input)

            # Step 2: Combine emotion guidance with user input
            modified_input = f"{emotion_guidance}\n\n{user_input}" if emotion_guidance else user_input

            # Step 3: Fetch chat history from memory
            memory_variables = memory.load_memory_variables({})
            chat_history = memory_variables.get("chat_history", [])

            # Step 4: Format the prompt
            prompt_text = self.prompt.format_prompt(
                user_input=modified_input,
                chat_history=chat_history
            ).to_string()

            # Step 5: Stream the response asynchronously
            response_text = ""
            try:
                print("Streaming response:")
                async for chunk in self.model.astream(prompt_text):  # Use llm.astream for async streaming
                    token = chunk.content  # Access token content
                    response_text += token
                    yield token  # Stream token immediately to the client

                print("\nFull Response:", response_text.strip())

                # Step 6: Update memory with the new messages
                memory.chat_memory.add_message({"role": "user", "content": user_input})
                memory.chat_memory.add_message({"role": "assistant", "content": response_text.strip()})

                # Step 7: Monitor memory usage
                self.monitor_memory(user_id)

            except Exception as e:
                logging.error(f"Error during streaming for user {user_id}: {e}")
                yield "Sorry, something went wrong. Let's try again."    
        
        
    def monitor_memory(self, user_id):
        """
        Monitor token usage and summarize memory if needed.
        
        Args:
            user_id (str): The unique identifier for the user.
        """
        
        memory = self.sessions[user_id]["memory"]
        total_tokens = 0

        try:
            # Load memory content
            memory_content = memory.load_memory_variables({}) or {}
            chat_history = memory_content.get("chat_history", [])

            # Iterate through chat history and count tokens
            for msg in chat_history:
                content = msg.get("content", "")
                if isinstance(content, str):
                    total_tokens += len(content.split())

            logging.info(f"Current token usage (approximate): {total_tokens}")  ## for testing purposes

            # Summarize if tokens exceed the limit
            if total_tokens > self.max_tokens_limit - 100:
                logging.info(f"Summarizing memory for user {user_id}...")
                memory.summarize()

        except Exception as e:
            logging.error(f"Error in monitor_memory for user {user_id}: {e}")          ## for testing purposes
            logging.info(f"Falling back to retaining recent messages.")
            self._retain_recent_messages(memory)
    
        
    def _retain_recent_messages(self, memory):
        """
        Retain recent messages in memory.
        
        Args:
            memory (ConversationSummaryBufferMemory):  Memory object to manage.
        """
        
        recent_messages = memory.chat_memory.messages[-self.max_history_length:]  # Keep last 3 interactions
        memory.chat_memory.clear()
        for msg in recent_messages:
            memory.chat_memory.add_message(msg)  
    
    
    def clear_memory(self, user_id):
        """
        Clear memory for a user.
        
        Args:
            user_id (str): The unique identifier for the user.
        """
        
        memory = self.sessions[user_id]["memory"]
        memory.chat_memory.clear()
        print(f"Memory cleared for user {user_id}")  
    
    
    def generate_emotion_prompt(self, user_input):
        """
        Generate an additional prompt based on the detected emotion.
        
        Args:
            user_input (str): User input text.
            
        Returns:
            str: Emotion-specific prompt or None.
        """
        try:
            emotion_tag = self.detect_emotion_tag(user_input)
            emotion_prompt = self.emotion_prompts.get(emotion_tag, "")
            return emotion_prompt
        
        except Exception as e:
            logging.error(f"Error generating emotion prompt: {e}")
            return ""
    