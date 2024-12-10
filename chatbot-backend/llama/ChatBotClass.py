from langchain_community.chat_models import ChatOllama
from langchain_core.prompts import (
    ChatPromptTemplate,
    MessagesPlaceholder,
    SystemMessagePromptTemplate,
    HumanMessagePromptTemplate,
)
from langchain.chains import LLMChain
from langchain.memory import ConversationSummaryBufferMemory
import torch
from emotion_detection.go_emotions import EmotionDetector   ## it should be installed first
################################# Class for Digital Companion with Memory #################################
## template : System Prompts -> String
## emotion_prompts : Dict (key: emotion, value: prompt)


class DigitalCompanion:
    
    def __init__(self, template, emotion_prompts, model_name="llama3.2:1b", temperature=0.7, top_p=0.9, max_tokens=100, max_tokens_limit=1500, max_history_length=3):
        
        device = "cuda" if torch.cuda.is_available() else "mps" if torch.backends.mps.is_available() else "cpu"
        self.llm = ChatOllama(model=model_name, temperature=temperature, max_tokens=max_tokens, device=device, stream=True)
        self.prompt = ChatPromptTemplate(
            messages=[
                SystemMessagePromptTemplate.from_template(template),
                MessagesPlaceholder(variable_name="chat_history"),
                HumanMessagePromptTemplate.from_template("{user_input}"),
            ]
        )
        self.max_tokens_limit = max_tokens_limit
        self.max_history_length = max_history_length
        self.emotion_prompts = emotion_prompts
        self.sessions = {}
        self.emotion_detector = self.initialize_emotion_detector() # initialize the emotion detector
        
    def create_session(self, user_id):
        """Create a new session for a user."""
        memory = ConversationSummaryBufferMemory(
            llm = self.llm,
            memory_key="chat_history",
            return_messages=True,
            max_history_length=self.max_history_length,
            max_token_limit=self.max_tokens_limit
        )
        
        """ chain = LLMChain(   ## maybe we should delete the chain
            llm = self.llm,
            prompt = self.prompt,
            verbose = False,    ##change to False, need for testing
            memory = memory
            
        ) """
        
        #self.sessions[user_id] = {"chain": chain, "memory": memory}
        self.sessions[user_id] = {"memory": memory}
        print(f"Session created for user {user_id}")
        
        
    def get_session(self, user_id):
        """Retrieve an existing session for a user."""
        
        if user_id not in self.sessions:
            raise ValueError(f"No session found for user {user_id}")
        
        return self.sessions[user_id]
    
    
    async def process_input(self, user_id, user_input):
        """Stream the response token by token using llm.astream."""
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
            async for chunk in self.llm.astream(prompt_text):  # Use llm.astream for async streaming
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
            print(f"Error during streaming: {e}")
            yield "Sorry, something went wrong. Let's try again."
    
    
    def monitor_memory(self, user_id):
        """Monitor token usage and summarize memory if needed."""
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

            print(f"Current token usage (approximate): {total_tokens}")  ## for testing purposes

            # Summarize if tokens exceed the limit
            if total_tokens > self.max_tokens_limit - 100:
                print(f"Summarizing memory for user {user_id}...")
                memory.summarize()

        except Exception as e:
            print(f"Error in monitor_memory: {e}")          ## for testing purposes
            print(f"Falling back to retaining recent messages.")
            self._retain_recent_messages(memory)
    
        
    def _retain_recent_messages(self, memory):
        """Retain recent messages in memory."""
        recent_messages = memory.chat_memory.messages[-self.max_history_length:]  # Keep last 3 interactions
        memory.chat_memory.clear()
        for msg in recent_messages:
            memory.chat_memory.add_message(msg)  
    
    
    def clear_memory(self, user_id):
        """Clear memory for a user."""
        memory = self.sessions[user_id]["memory"]
        memory.chat_memory.clear()
        print(f"Memory cleared for user {user_id}")  
    
    
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
            raise ValueError("Emotion detector is not initialized.")
        
        emotion_data = self.emotion_detector.detect_emotion(user_input)
        return emotion_data["primary_emotion"]   # return the primary emotion tag
    
    
    def generate_emotion_prompt(self, user_input):
        """
        Generate an additional prompt based on the detected emotion.
        """
        try:
            emotion = self.detect_emotion_tag(user_input)
            return self.emotion_prompts.get(emotion, "")   ## here we return the prompt based on the emotion
        
        except Exception as e:
            #print(f"Error detecting emotion: {e}")  ## for testing purposes
            return ""
    
