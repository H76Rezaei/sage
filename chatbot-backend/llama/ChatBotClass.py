from langchain_community.chat_models import ChatOllama
from langchain_core.prompts import (
    ChatPromptTemplate,
    MessagesPlaceholder,
    SystemMessagePromptTemplate,
    HumanMessagePromptTemplate,
)
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser
from langchain.memory import ConversationBufferMemory

import torch
from emotion_detection.go_emotions import EmotionDetector
import os
from langchain.vectorstores import Pinecone as LangchainPinecone
from langchain_community.embeddings import OllamaEmbeddings
from pinecone import Pinecone, ServerlessSpec
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage, SystemMessage
from datetime import datetime, timedelta
import time
import asyncio
from typing import Dict, List
from langchain.chains.summarize import load_summarize_chain
from langchain.docstore.document import Document
from langchain.chains import LLMChain
from langchain_core.prompts import PromptTemplate

load_dotenv()

class DigitalCompanion:
    def __init__(self, template, emotion_prompts, model_name="llama3.2:1b", temperature=0.6, max_tokens=128, max_tokens_limit=1500):
        device = "cuda" if torch.cuda.is_available() else "mps" if torch.backends.mps.is_available() else "cpu"
        self.llm = ChatOllama(
            model=model_name, 
            temperature=temperature, 
            max_tokens=max_tokens,
            device=device, 
            stream=True,
            stop=["\n\n\n"]
        )
        
        self.prompt = ChatPromptTemplate.from_messages([
            SystemMessagePromptTemplate.from_template(template),
            MessagesPlaceholder(variable_name="long_term_memory"),
            MessagesPlaceholder(variable_name="recent_conversation"),
            HumanMessagePromptTemplate.from_template("{input}")
        ])
        
        self.max_tokens_limit = max_tokens_limit
        self.emotion_prompts = emotion_prompts
        self.sessions = {}
        self.emotion_detector = self.initialize_emotion_detector()
        
        # Initialize Pinecone and store it as instance variable
        self.vectorstore = self._initialize_pinecone(model_name)

        # Add summarization chain
        self.summary_prompt = PromptTemplate(
            input_variables=["text"],
            template="""Extract from conversation:
                        - Main topic and intent 
                        - Key decisions/outcomes
                        - Action items
                        - User sentiment
                        - Important entities
                        - Time-sensitive details
                        - Critical context/background
                        Context: {text}"""
        )
        self.summary_chain = LLMChain(llm=self.llm, prompt=self.summary_prompt)
        
        # Modified memory management
        self.context_window = 5  # Number of messages to summarize
    
    def _initialize_pinecone(self, model_name):
        api_key = os.getenv("PINECONE_API_KEY")
        if not api_key:
            raise ValueError("PINECONE_API_KEY not found in environment variables")
        
        self.embeddings = OllamaEmbeddings(model=model_name)
        test_embedding = self.embeddings.embed_query("test")
        embedding_dimension = len(test_embedding)
        
        self.pc = Pinecone(api_key=api_key)
        index_name = "chatbot-memory"
        
        if index_name not in self.pc.list_indexes().names():
            self.pc.create_index(
                name=index_name,
                dimension=embedding_dimension,
                metric="cosine",
                spec=ServerlessSpec(cloud="aws", region="us-east-1")
            )
        
        return LangchainPinecone.from_existing_index(
            index_name=index_name,
            embedding=self.embeddings,
            namespace="chatbot"
        )
            
    def create_session(self, user_id):
        """Create a new session with balanced memory management."""
        buffer_memory = ConversationBufferMemory(
            return_messages=True,
            memory_key="recent_conversation",
            input_key="input"
        )
        def get_memory(input_dict):
            user_input = input_dict["input"].strip().lower()

            # Skip memory lookup for short or trivial messages
            if len(user_input) < 5 or user_input in {"hi", "hello", "hey"}:
                return {
                    "recent_conversation": buffer_memory.load_memory_variables({}).get("recent_conversation", [])[-6:],
                    "long_term_memory": []
                }

            # Get recent conversation (short-term memory)
            memory_vars = buffer_memory.load_memory_variables({})
            recent_conversation = memory_vars.get("recent_conversation", [])

            return {
                "recent_conversation": recent_conversation[-6:],
                "long_term_memory": []  # Long-term memory will be handled in process_input
            }
        chain = (
            RunnablePassthrough.assign(
                recent_conversation=lambda x: get_memory(x)["recent_conversation"],
                long_term_memory=lambda x: get_memory(x)["long_term_memory"]
            )
            | self.prompt 
            | self.llm 
            | StrOutputParser()
        )
        
        self.sessions[user_id] = {
            "chain": chain,
            "buffer_memory": buffer_memory,
            "conversation_context": []
        }
        
        print(f"Session created for user {user_id}")
        

    async def summarize_context(self, messages: List[BaseMessage]) -> Dict:
        """Generate summary of conversation context."""
        if not messages:
            return {}
        
        # Create combined_text here before using it
        combined_text = "\n".join([f"{msg.__class__.__name__}: {msg.content}" for msg in messages])
        summary = await self.summary_chain.arun(combined_text)
    
        return summary

    async def process_input(self, user_id, user_input):
        """Process user input with balanced context management."""
        if user_id not in self.sessions:
            self.create_session(user_id)
        
        session = self.sessions[user_id]
        
        try:
            emotion_guidance = self.generate_emotion_prompt(user_input)
            modified_input = f"{emotion_guidance}\n\n{user_input}" if emotion_guidance else user_input
            
            # Enhanced retrieval with both summaries and conversations
            relevant_docs = self.vectorstore.similarity_search_with_score(
                user_input,
                k=3,
                filter={
                    "user_id": user_id,
                    "timestamp": {"$gte": time.time() - (90 * 24 * 60 * 60)}
                }
            )
            
            # Combine retrieved context and create memory messages
            long_term_memory = []
            for doc, score in relevant_docs:
                if score > 0.70:  # Relevance threshold
                    if doc.metadata.get("type") == "summary":
                        context = f"Previous context summary: {doc.page_content}"
                    else:
                        context = f"Previous conversation: {doc.page_content}"
                    if context.strip():
                        long_term_memory.append(SystemMessage(content=context))
            
            # Update conversation context
            session["conversation_context"].append(modified_input)
            recent_conversation = [
                HumanMessage(content=msg) if i % 2 == 0 else AIMessage(content=msg)
                for i, msg in enumerate(session["conversation_context"][-6:])
            ]
            
            # Generate and stream response
            response = await session["chain"].ainvoke({"input": modified_input, "long_term_memory": long_term_memory, "recent_conversation": recent_conversation})
            for token in response.split():
                yield token + " "
            
            # Update memories
            session["buffer_memory"].chat_memory.add_user_message(modified_input)
            session["buffer_memory"].chat_memory.add_ai_message(response)
            
            # Update conversation context
            if len(session["conversation_context"]) > 5:
                session["conversation_context"] = session["conversation_context"][-5:]
        
            self.vectorstore.add_texts(
                texts=[f"Human: {modified_input}\nAI: {response}"],
                metadatas=[{
                    "user_id": user_id,
                    "timestamp": time.time(),
                    "type": "conversation",
                    "keywords": modified_input.lower().split()[:10],
                    "context": " ".join(session["conversation_context"])
                }],
                namespace="chatbot"
            )
            # Manage memory size
            self.monitor_memory(user_id)
            
        except Exception as e:
            print(f"Error during processing: {e}")
            yield "Sorry, something went wrong. Let's try again."
    
    def monitor_memory(self, user_id):
        """Monitor and manage memory usage."""
        if user_id not in self.sessions:
            return
        
        buffer_memory = self.sessions[user_id]["buffer_memory"]
        
        if len(buffer_memory.chat_memory.messages) > self.context_window:
            messages_to_summarize = buffer_memory.chat_memory.messages[:-self.context_window]
            
            # Generate and store summary asynchronously
            asyncio.create_task(self.summarize_and_store(user_id, messages_to_summarize))
            
            # Keep recent messages
            buffer_memory.chat_memory.messages = buffer_memory.chat_memory.messages[-self.context_window:]
    
    async def summarize_and_store(self, user_id, messages):
        """Helper method to summarize and store conversation chunks."""
        summary = await self.summarize_context(messages)
        if summary:
            self.vectorstore.add_texts(
                texts=[summary],
                metadatas=[{
                    "user_id": user_id,
                    "timestamp": time.time(),
                    "type": "summary"
                }],
                namespace="chatbot-summaries"
            )    
    def initialize_emotion_detector(self):
        """Initialize and return the emotion detector instance."""
        return EmotionDetector()
    
    def detect_emotion_tag(self, user_input):
        """Detect the primary emotion from the user input and return it as a tag."""
        if not self.emotion_detector:
            raise ValueError("Emotion detector is not initialized.")
        
        emotion_data = self.emotion_detector.detect_emotion(user_input)
        return emotion_data["primary_emotion"]
    
    def generate_emotion_prompt(self, user_input):
        """Generate an additional prompt based on the detected emotion."""
        try:
            emotion = self.detect_emotion_tag(user_input)
            return self.emotion_prompts.get(emotion, "")
        except Exception as e:
            return ""
