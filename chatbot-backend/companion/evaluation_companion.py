from emotion.emotion_handler import EmotionHandler
from model.model_utils import init_model
from langgraph.graph import START, MessagesState, StateGraph
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.runnables import RunnableConfig
from model.prompt_manager import PromptManager
from memory.memory_manager import MemoryManager
from langchain_core.messages import trim_messages
from langchain_core.messages import HumanMessage
from langchain_core.messages.modifier import RemoveMessage

import logging

class DigitalCompanion:
    
    MAX_CONTEXT_TOKENS = 128_000
  
    def __init__(self, 
                 params: dict,
                 index_name = "chatbot-eval-memory",
                 user_id = "test-user",
                 thread_id = "test-session"):
        
            
        self.model = init_model(model=params['model_name'], temperature=params['temperature'], max_tokens=params['max_tokens'], top_p=params['top_p'], device=params['hardware'], stream=params['streaming'])
        self.max_tokens = params['max_tokens']
            
        self.memory_manager = MemoryManager(model=self.model,
                                           user_id=user_id,
                                           thread_id=thread_id,
                                           index_name=index_name,
                                           embedding_model=params['embedding_model'],
                                           embedding_dim=params['embedding_dim'],
                                           max_results=params['max_db_results'],
                                           score_threshold=params['similarity_threshold'],
                                           stm_limit=params['max_history_length'])
        
        self.prompt_manager = PromptManager(system_prompt= params['system_prompt'])
        self.emotion_handler = EmotionHandler(params['emotion_prompts'])
        self.user_id = user_id
        self.thread_id = thread_id    
        self.config = self.setup_config()
        self.app = self.setup_workflow()
        self.bound = self.prompt_manager.prompt_template | self.model 
        self.trimmer = trim_messages(strategy = "last", max_tokens = params['max_history_length'], token_counter= len)
        self.output_tokens = None
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
            logging.info(f"Trimmed short-term memory: {stm_messages}")
            
            # Step 3: Retrieve relevant long-term memories
            relevant_memories = await self.memory_manager.retrieve_relevant_context(query=user_input)
            logging.info(f"Retrieved relevant memories: {relevant_memories}")
            
            # Step 4: Generate emotion guidance
            detected_emotion, emotion_guidance = self.emotion_handler.generate_emotion_prompt(user_input)
            logging.info(f"Generated emotion guidance: {emotion_guidance}")
            
            valid_input_size = self.prompt_manager.validate_prompt_size(self.model, detected_emotion, emotion_guidance, relevant_memories, stm_messages, self.max_tokens)
            
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
                
                self.output_tokens = response.usage_metadata['output_tokens']    
                logging.info(f"metadata: response.usage_metadata: {response.usage_metadata}")    
                 
        
        except Exception as e:
            logging.error(f"Error in call_model: {e}")
            # Add context to the exception and re-raise
            raise RuntimeError(f"call_model: Failed to process input for user: {config['configurable'].get('thread_id')}.") from e
    
    
    async def stream_workflow_response(self, user_input: str):
        """
        Streams the response for the given user input and retrieves output tokens.

        Args:
            user_input (str): The user's input message.

        Yields:
            str: Each token streamed during the response.
            tuple: Final (response_text, output_tokens_count) after streaming completes.
    """
        inputs = [HumanMessage(content=user_input)]
        response_text = ""

        try:
            logging.info("Starting to stream the response...")

            # Stream tokens as they are generated
            async for msg, metadata in self.app.astream({"messages": inputs}, config=self.config, stream_mode="messages"):
                if msg.content and not isinstance(msg, HumanMessage):
                    token = msg.content
                    response_text += token
                    yield token  # Yield each token during streaming

           
        except Exception as e:
            logging.error(f"Error during streaming: {e}")
            raise RuntimeError("Error during streaming response.") from e
        

            
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
        """
        Retrieves the number of output tokens from the latest AI response.

        Returns:
            int: The number of output tokens from the response metadata.
        """
            
        return self.output_tokens