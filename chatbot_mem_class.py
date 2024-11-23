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

################################# Class for Digital Companion with Memory #################################

class DigitalCompanion:
    
    def __init__(self, template, model_name="llama3.2:1b", temperature=0.6, max_tokens=128, max_tokens_limit=1500, max_history_length=3):
        device = "cuda" if torch.cuda.is_available() else "mps" if torch.backends.mps.is_available() else "cpu"
        self.llm = ChatOllama(model=model_name, temperature=temperature, max_tokens=max_tokens, device=device)
        self.prompt = ChatPromptTemplate(
            messages=[
                SystemMessagePromptTemplate.from_template(template),
                MessagesPlaceholder(variable_name="chat_history"),
                HumanMessagePromptTemplate.from_template("{user_input}"),
            ]
        )
        self.max_tokens_limit = max_tokens_limit
        self.max_history_length = max_history_length
        self.sessions = {}
      
        
    def create_session(self, user_id):
        """Create a new session for a user."""
        memory = ConversationSummaryBufferMemory(
            llm = self.llm,
            memory_key="chat_history",
            return_messages=True,
            max_history_length=self.max_history_length,
            max_token_limit=self.max_tokens_limit
        )
        
        chain = LLMChain(
            llm = self.llm,
            prompt = self.prompt,
            verbose = False, ##change to False, need for testing
            memory = memory
            
        )
        
        self.sessions[user_id] = {"chain": chain, "memory": memory}
        print(f"Session created for user {user_id}")
        
        
    def get_session(self, user_id):
        """Retrieve an existing session for a user."""
        
        if user_id not in self.sessions:
            raise ValueError(f"No session found for user {user_id}")
        
        return self.sessions[user_id]
    
    
    def process_input(self, user_id, user_input):
        """Process user input and return the chatbot response."""
        
        if user_id not in self.sessions:
            self.create_session(user_id)
            
        chain = self.sessions[user_id]["chain"]
        memory = self.sessions[user_id]["memory"]
        
        ### it should be completed and return response
        try:
            response = chain({"user_input": user_input})
            #print(response["text"])  # for testing purposes
            self.monitor_memory(user_id)
            return response["text"]
        except ValueError as e:
            print(f"Token limit exceeded for user {user_id}. Retaining recent messages.") # for testing purposes
            self._retain_recent_messages(memory) 
            return "Let's Continue the conversation."
            
        
    def monitor_memory(self, user_id):
        """Monitor token usage and summarize memory if needed."""
        memory = self.sessions[user_id]["memory"]
        total_tokens = 0
        memory_content = memory.load_memory_variables({})
        
        for value in memory_content.values():
            for msg in value:
                total_tokens += len(msg.content.split())  # Count tokens in each message
        
        #print(f"Current token usage (approximate): {total_tokens}")   # for testing purposes
        
        if total_tokens > self.max_tokens_limit - 100:  # Adjust threshold as needed
            #print(f"[User {user_id}] Summarizing memory to avoid overflow.")    # for testing purposes
            memory.summarize()
    
    
    def _retain_recent_messages(self, memory):
        """Retain recent messages in memory."""
        recent_messages = memory.chat_memory.messages[-self.max_history_length:]  # Keep last 3 interactions
        memory.chat_memory.clear()
        for msg in recent_messages:
            memory.chat_memory.add_message(msg)    
        