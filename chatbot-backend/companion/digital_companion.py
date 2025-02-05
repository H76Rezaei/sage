from emotion.emotion_handler import EmotionHandler
from model.model_utils import init_model, load_json_config
from langgraph.graph import START, MessagesState, StateGraph
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.runnables import RunnableConfig
from utils.supabase_utils import fetch_prompt_data
from model.prompt_manager import PromptManager
from memory.memory_manager import MemoryManager
from langchain_core.messages import trim_messages
from langchain_core.messages import AIMessageChunk, HumanMessage, AIMessage
from langchain_core.messages.modifier import RemoveMessage
import torch
import logging
import os



class DigitalCompanion:
    
    MAX_CONTEXT_TOKENS = 128_000
    _model = None

    #add you hugging face api key to companion/default_model_config.json
    #as follows:
    """
    {
    "model": "meta-llama/Llama-3.2-1B-Instruct",
    "temperature": 0.5,
    "max_tokens": 100,
    "top_p": 0.7,
    "stream": true,
    "api_key": ""
    }
    """
    print("I hope you added your huggingFace api key to default_model_config.json")
    config_path = os.path.join(os.path.dirname(__file__), "default_model_config.json")

    system_prompt, emotion_prompts = fetch_prompt_data(system_id=13, emotion_group_id=5)
    prompt_manager = PromptManager(system_prompt= system_prompt)
    emotion_handler = EmotionHandler(emotion_prompts)
    
    @classmethod
    def get_model(cls, config):
        """
        Lazily initialize and return the shared model instance.
        Args:
            config (dict): Configuration dictionary for the model.
        """
        if cls._model is None:
            
            config['device'] = ("cuda" if torch.cuda.is_available() 
                                else "mps" if torch.backends.mps.is_available() 
                                else "cpu")
            
            
            cls._model = init_model(**config)
            logging.info(f"Initialized model: {cls._model}")
            
        return cls._model
    
    
    def __init__(self, 
                 custom_config=None,
                 stm_limit=7,
                 index_name = "chatbot-memory",
                 embedding_model = 'intfloat/multilingual-e5-large',
                 score_threshold = 0.8,
                 max_db_results = 3,
                 embedding_dim = 1024,
                 user_id = "test_user",
                 thread_id = "test_session"):
        
        config = load_json_config(self.config_path)
        if custom_config:
            config.update(custom_config)
            
        self.model = self.get_model(config)
        self.max_tokens = config["max_tokens"]
            
        self.memory_manager = MemoryManager(model=self.model,
                                           user_id=user_id,
                                           thread_id=thread_id,
                                           index_name=index_name,
                                           embedding_model=embedding_model,
                                           embedding_dim=embedding_dim,
                                           max_results=max_db_results,
                                           score_threshold=score_threshold,
                                           stm_limit=stm_limit)
        self.user_id = user_id
        self.thread_id = thread_id    
        self.config = self.setup_config()
        self.app = self.setup_workflow()
        self.bound = DigitalCompanion.prompt_manager.prompt_template | self.model 
        self.trimmer = trim_messages(strategy = "last", max_tokens = stm_limit, token_counter= len)
    ############################################################################################################  
    def setup_config(self) -> RunnableConfig:
        
        return RunnableConfig(configurable={"user_id": self.user_id, 'thread_id': self.thread_id})   
    
    ############################################################################################################
    def setup_workflow(self):    
        """
        Sets up and initializes the workflow for processing input using the StateGraph.

        This method defines the workflow structure, including nodes, edges, and a memory checkpointer, and compiles it into an executable application.

        Returns:
            app: The compiled StateGraph application, ready to process input and manage state transitions.

        Notes:
            - The `self.call_model` method is expected to be defined in the class and used as the node's processing function.
            - The `MemorySaver` checkpointer keeps the state in memory, making this suitable for short-term or in-memory workflows.
        """
        workflow = StateGraph(state_schema=MessagesState)
        # Define the node and edge
        workflow.add_node("model", self.call_model)
        workflow.add_edge(START, "model")
        
        # Add simple in-memory checkpointer
        memory = MemorySaver()
        app = workflow.compile(checkpointer=memory)
        return app
    
    ############################################################################################################   
        
    async def prepare_context(self, user_input: str):
        """Prepares context for streaming response"""
        temp_state = MessagesState(messages=[HumanMessage(content=user_input)])
        
        await self.memory_manager.transfer_excess_to_ltm(temp_state)
        stm_messages = self.trimmer.invoke(temp_state["messages"])
        relevant_memories = await self.memory_manager.retrieve_relevant_context(query=user_input)
        detected_emotion, emotion_guidance = DigitalCompanion.emotion_handler.generate_emotion_prompt(user_input)
        
        prompt = DigitalCompanion.prompt_manager.prompt_template.format_prompt(
            messages=stm_messages,
            detected_emotion=detected_emotion,
            emotion_prompt=emotion_guidance,
            recall_memories="\n".join(relevant_memories)
        ).to_string()

        prompt += "\nAI:"
        
        return prompt

    async def stream_workflow_response(self, user_input: str):
        """Streams response using direct HuggingFace client streaming"""
        try:
            # Get formatted prompt
            prompt = await self.prepare_context(user_input)
            print("prompt:", prompt)

            accumulated_response = ""
            
            # Stream directly using HuggingFace client
            stream = self.model._client.text_generation(
                prompt,
                model=self.model.model_name,
                max_new_tokens=self.model.max_new_tokens,
                temperature=self.model.temperature,
                top_p=self.model.top_p,
                stream=True,
                details=True,
                stop=["<|eot_id|>", "Human:", "AI:"]
            )
            
            for response in stream:
                if hasattr(response, 'token') and hasattr(response.token, 'text'):
                    token_text = response.token.text
                    accumulated_response += token_text
                    yield token_text

            # Post-process accumulated response
            accumulated_response = accumulated_response.split("<|eot_id|>")[0].split("Human:")[0].strip()
            accumulated_response = accumulated_response.split("AI:")[0].strip()
            print("accumulated resposne ",accumulated_response)
            
            # Update workflow state after streaming completes
            self.app.update_state(
                self.config,
                {"messages": [
                    HumanMessage(content=user_input),
                    AIMessage(content=accumulated_response)
                ]}
            )
            
        except Exception as e:
            logging.error(f"Error during streaming: {e}", exc_info=True)
            raise

    async def call_model(self, state: MessagesState, config: RunnableConfig) -> dict:
        """Non-streaming model call used by the workflow graph"""
        try:
            user_input = state["messages"][-1].content
            await self.memory_manager.transfer_excess_to_ltm(state)
            stm_messages = self.trimmer.invoke(state["messages"])
            
            relevant_memories = await self.memory_manager.retrieve_relevant_context(query=user_input)
            detected_emotion, emotion_guidance = DigitalCompanion.emotion_handler.generate_emotion_prompt(user_input)
            
            if DigitalCompanion.prompt_manager.validate_prompt_size(
                self.model, detected_emotion, emotion_guidance, 
                relevant_memories, stm_messages, self.max_tokens
            ):
                prompt = DigitalCompanion.prompt_manager.prompt_template.format_prompt(
                    messages=stm_messages,
                    detected_emotion=detected_emotion,
                    emotion_prompt=emotion_guidance,
                    recall_memories="\n".join(relevant_memories)
                ).to_string()
                
                # Use HuggingFace client directly
                response = self.model._client.text_generation(
                    prompt,
                    model=self.model.model_name,
                    max_new_tokens=self.model.max_new_tokens,
                    temperature=self.model.temperature,
                    top_p=self.model.top_p,
                    details=True,
                    stop=["<|eot_id|>", "Human:", "AI:"]
                )
                # Process generated text
                response.generated_text = response.generated_text.split("<|eot_id|>")[0].split("Human:")[0].strip()
                
                return {"messages": AIMessage(content=response.generated_text)}
                
        except Exception as e:
            logging.error(f"Error in call_model: {e}", exc_info=True)
            raise RuntimeError(f"call_model failed: {str(e)}")

    async def process_input(self, user_input: str):
        """Non-streaming input processing"""
        response = await self.app.ainvoke(
            {"messages": [HumanMessage(content=user_input)]},
            config=self.config
        )
        return response["messages"].content
    
    
    
    async def clear_short_term_memory(self) -> None:
            
        try:
            # Fetch all messages from the state
            messages = self.app.get_state(self.config).values["messages"]

            # Remove each message individually
            for message in messages:
                self.app.update_state(self.config, {"messages": RemoveMessage(id=message.id)})
                logging.info(f"Deleted message with ID: {message.id}")

            logging.info("Successfully cleared short-term memory.")
        except Exception as e:
            logging.error(f"Error clearing short-term memory: {e}")
            raise RuntimeError("Failed to clear short-term memory.") from e
    
    
    async def clear_all_memories(self) -> None:
        """
        Clear both short-term and long-term memory for the user.
        """
        await self.clear_short_term_memory()
        await self.memory_manager.clear_long_term_memory()
        logging.info("Successfully cleared all memories.")
        
    
    
    def get_output_tokens_count(self):
        
        return self.app.get_state(self.config).values['messages'][-1].usage_metadata['output_tokens']
