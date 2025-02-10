from emotion.emotion_handler import EmotionHandler
from model.model_utils import init_model, load_json_config
from langgraph.graph import START, MessagesState, StateGraph
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.runnables import RunnableConfig
from utils.supabase_utils import fetch_prompt_data
from model.prompt_manager import PromptManager
from memory.memory_manager import MemoryManager
from langchain_core.messages import trim_messages
from langchain_core.messages import AIMessageChunk, HumanMessage
from langchain_core.messages.modifier import RemoveMessage
import torch
import logging
import os


class DigitalCompanion:
    
    MAX_CONTEXT_TOKENS = 128_000
    _model = None
    config_path = os.path.join(os.path.dirname(__file__), "default_model_config.json")

    system_prompt, emotion_prompts = fetch_prompt_data(system_id=17, emotion_group_id=6)
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
            
            #cls._model = ChatOllama(**config)
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
                 user_id = "test_3_with_demo_script",
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
        
    async def call_model(self, state: MessagesState, config: RunnableConfig) -> dict:
        """
        Processes the current conversation state and generates a response using the model.

        Args:
            state (MessagesState): The current state of the conversation, containing messages and context.
            config (RunnableConfig): Configuration object with runtime parameters.

        Returns:
            dict: A dictionary containing the AI's response as a list of messages.

        Workflow:
            1. Manage memory by saving excess messages to long-term memory.
            2. Trim short-term memory (STM) messages to fit within the token limit.
            3. Retrieve relevant long-term memories based on the user's input.
            4. Generate an emotion-guided system prompt based on the user's input.
            5. Call the model with STM messages and retrieved memories to generate a response.

        Error Handling:
            - Logs any errors that occur during processing.
            - Raises the exception with additional context.

        Raises:
            Exception: If any error occurs during processing.
        """    
        
        try:
            
            user_input = state["messages"][-1].content
            
            await self.memory_manager.transfer_excess_to_ltm(state)
            
            stm_messages = self.trimmer.invoke(state["messages"])
            #logging.info(f"Trimmed short-term memory: {stm_messages}")
            
            # Step 3: Retrieve relevant long-term memories
            relevant_memories = await self.memory_manager.retrieve_relevant_context(query=user_input)
            #logging.info(f"Retrieved relevant memories: {relevant_memories}")
            
            # Step 4: Generate emotion guidance
            detected_emotion, emotion_guidance = DigitalCompanion.emotion_handler.generate_emotion_prompt(user_input)
            #logging.info(f"Generated emotion guidance: {emotion_guidance}")
            
            valid_input_size = DigitalCompanion.prompt_manager.validate_prompt_size(self.model, detected_emotion, emotion_guidance, relevant_memories, stm_messages, self.max_tokens)
            
            if valid_input_size:
                
                response = await self.bound.ainvoke(
                        {
                            "messages": stm_messages,
                            "detected_emotion": detected_emotion,
                            "emotion_prompt": emotion_guidance,
                            "recall_memories": relevant_memories,
                        },
                        config
                    )
                    
                #print(f"metadata: response.usage_metadata: {response.usage_metadata}")    ## response.usage_metadata[output_tokens]
                return {"messages": response}
        
        except Exception as e:
            logging.error(f"Error in call_model: {e}")
            # Add context to the exception and re-raise
            raise RuntimeError(f"call_model: Failed to process input for user: {config['configurable'].get('thread_id')}.") from e
    
    
    
    async def stream_workflow_response(self, user_input:str):
        # Replace the input with your user's query
        inputs = [HumanMessage(content=user_input)]
        first = True
        gathered = None
        
        try:
            #logging.info("Starting to stream the response...")
            #print("Streaming response:\n"
            #      )
            # Here we specify stream_mode="messages" to get token-level updates.
            async for msg, metadata in self.app.astream({"messages": inputs}, config=self.config, stream_mode="messages"):
                # Only print AI message content (chunks), exclude Human messages
                if msg.content and not isinstance(msg, HumanMessage):
                    token = msg.content
                    #print(token, end="", flush=True)
                    yield token

                if isinstance(msg, AIMessageChunk):
                    # Accumulate AIMessageChunks to form a complete AIMessage at the end if needed
                    if first:
                        gathered = msg
                        first = False
                    else:
                        gathered = gathered + msg

            #logging.info("Streaming completed successfully.")
            #output_tokens_count = self.app.get_state(self.config).values['messages'][-1].usage_metadata['output_tokens']
            #print(f"state: {output_tokens_count}")    

            
        except Exception as e:
            print(f"Error during streaming: {e}")
    
    
    
    
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
