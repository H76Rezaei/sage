from langchain_core.prompts import ChatPromptTemplate
 
import torch
from emotion_detection.go_emotions import EmotionDetector   
from langchain_ollama  import ChatOllama
import torch
from typing import List, Union

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
import logging
import uuid
   
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import START, MessagesState, StateGraph
from langgraph.graph import MessagesState

from langchain_core.messages import trim_messages
from langchain_core.runnables import RunnableConfig
from langchain_core.messages import AIMessageChunk, HumanMessage
from pinecone_utils import setup_vector_store, initialize_pinecone, get_retriever
from prompt_handler import fetch_prompt_data
from langchain_core.messages.modifier import RemoveMessage
from model_initializer import init_model
################################# Class for Digital Companion with Memory #################################
## template : System Prompts -> String
## emotion_prompts : Dict (key: emotion, value: prompt)

pc = initialize_pinecone()

MAX_CONTEXT_TOKENS = 128_000

system_prompt = """

### Instruction ###
You are Sage, a conversational AI companion for elderly users, offering empathy and practical help.\n\n  
1. **After this initial greeting, do not repeat the name of user unless it is necessary or he/she explicitly requests it.**  
2. Keep every response to a maximum of 3 sentences.  
3. When the user asks for hobbies or activities, provide exactly 2–3 simple suggestions.  
4. Do not begin answers with phrases like “I’m sorry” or “It’s normal.”  
5. If the topic changes, move on without revisiting older topics unless prompted.  
6. If the user refuses suggestions, ask if there is anything else you can help with, then move on.  
7. If the user thanks or compliments you, acknowledge kindly and offer further help.  
8. If asked about your name or identity, clearly state you are Sage.  
9. Do not begin responses with “AI:” or “Bot:”.  
10. answers in warm and natural way.

### Example Conversation Demonstrating These Rules ###

**Human:** "Hi, my name is Laura. I feel so lonely these days."  
**AI:**  
"Hi, Laura! It can be tough to feel lonely, especially when it feels like everyone around you is busy or distant.  
Would you like to talk about what’s on your mind or try some new activities?"

**Human:** "I lost my partner last year. I don’t know how to move on."  
**AI:**  
"Losing someone close can feel overwhelming, and grief may linger for a while.  
Sometimes sharing your thoughts helps you process them, and it’s okay to take it one day at a time.  
Would you like some ideas for comforting activities or hobbies?"

**Human:** "Can you suggest me some hobbies that help me to move on?"  
**AI:**  
"Gentle gardening or cooking can be soothing and keep your mind engaged.  
You might also consider journaling or painting to express your emotions.  
Would you like more suggestions?"
"""


class DigitalCompanion:
    
    max_tokens = 30
    shared_model = None
    
    
    emotion_detector = EmotionDetector()
    _, emotion_prompts = fetch_prompt_data()
    
    @classmethod
    def set_shared_model(cls, **model_params):
        """
        Set the shared model for all instances of DigitalCompanion.

        Args:
            model_params: Parameters to configure the shared model (e.g., model_name, temperature).
        """
        if cls.shared_model is None:
            cls.shared_model = init_model(**model_params)
            cls.max_tokens = model_params.get("max_tokens", cls.max_tokens)
        else:
            raise ValueError("Shared model is already initialized and cannot be reinitialized.")  
    
    
    def __init__(self,   
                 max_tokens_limit=1500, 
                 stm_limit=7,
                 index_name = "chatbot-memory",
                 embedding_model = 'intfloat/multilingual-e5-large',
                 score_threshold = 0.8,
                 max_db_results = 3,
                 embedding_dim = 1024,
                 user_id = "test_user",
                 thread_id = "test_session"
                 ):
        
        self.config = self.setup_config(user_id, thread_id)
        self.user_id = user_id 
        self.thread_id  = thread_id
        self.is_saved_in_pinecone = False
        
        self.vector_store = setup_vector_store(pc=pc, index_name=index_name, embed_model=embedding_model, embed_dim=embedding_dim)
        self.retriever = get_retriever(vector_store=self.vector_store, max_results=max_db_results , score_threshold=score_threshold, namespace=self.user_id)
        self.prompt = self.format_prompt(system_prompt)
        self.stm_limit = stm_limit
        self.trimmer = trim_messages(strategy = "last", max_tokens = stm_limit, token_counter= len)
        self.app = self.setup_workflow()

        self.max_tokens_limit = max_tokens_limit
        
    
    ############################################################################################################   
    def format_prompt(self, system_prompts: str) -> ChatPromptTemplate:
        
        """ 
        Creates a formatted ChatPromptTemplate using the provided system prompts and placeholders 
        for recall memories, emotional guidance, and message history.

        Args:
            system_prompts (str): The system prompt text that describes the AI's behavior and instructions for the model.

        Returns:
            ChatPromptTemplate: A ChatPromptTemplate object containing the formatted system prompt, 
            placeholders for recall memories, emotional guidance, and conversational history.
        """
        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system", f"""{system_prompts}\n\n
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
         
        return prompt   
    
    ############################################################################################################  
    def setup_config(self, user_id: str, thread_id: str) -> RunnableConfig:
        
        return RunnableConfig(configurable={"user_id": user_id, 'thread_id': thread_id})
     
    ############################################################################################################
    
    
    ############################################################################################################   
        
    async def save_to_LTM(self, messages: List[Union[AIMessage, HumanMessage]]) -> str: ## save to Pinecone
        """
        Save a list of Human and AI messages to Pinecone as long-term memory (LTM).

        This function combines all the provided messages into a single string, with each message
        prefixed by its type ("Human" for `HumanMessage` and "AI" for `AIMessage`), and stores the
        resulting string in Pinecone under the specified namespace and thread ID.

        Args:
            messages (List[Union[AIMessage, HumanMessage]]): 
                A list of `AIMessage` and `HumanMessage` objects to be saved in long-term memory.

        Returns:
            str: A single string combining all the input messages with their respective types, 
            ready for storage in Pinecone.

        """
        combined_messages = []
        for msg in messages:
            if isinstance(msg, HumanMessage):
                combined_messages.append(f"Human: {msg.content}")
            
            elif isinstance(msg,AIMessage):
                summerized_msg = await self.summerize_AI_message(msg.content)
                combined_messages.append(f"AI: {summerized_msg}")
        
        combined_messages = "\n".join(combined_messages)
        
        await self.vector_store.aadd_texts(
            texts = [combined_messages],
            namespace = self.user_id,
            metadatas = [{'session_id':self.thread_id}],
            ids = [str(uuid.uuid4())],
            
        )
        self.is_saved_in_pinecone = True
        return combined_messages
    
    ############################################################################################################    
    async def retrieve_relevant_context(self, query: str) -> List[str]:
    
        """
        Retrieves relevant context from the retriever based on the provided query and session filter.

        Args:
            query (str): The query string for which relevant context needs to be retrieved.
            config (RunnableConfig): Configuration object containing necessary runtime parameters.

        Returns:
            list[str]: A list of strings containing the page content of the relevant documents retrieved.
            
        """
        
        docs = await self.retriever.ainvoke(query, filter={"session_id": self.thread_id})  
        results = [doc.page_content for doc in docs]
        
        return results

    
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
            # Prepare the prompt and model binding
            bound = self.prompt | DigitalCompanion.model
            
            # Retrieve user input (latest message)
            user_input = state["messages"][-1].content
            
            # Step 1: Manage memory
            await self.manage_memory(state)
            
            # Step 2: Trim short-term memory (STM) messages
            stm_messages = self.trimmer.invoke(state["messages"])
            logging.info(f"Trimmed short-term memory: {stm_messages}")
            
            # Step 3: Retrieve relevant long-term memories
            relevant_memories = await self.retrieve_relevant_context(query=user_input)
            logging.info(f"Retrieved relevant memories: {relevant_memories}")
            
            # Step 4: Generate emotion guidance
            detected_emotion, emotion_guidance = self.generate_emotion_prompt(user_input)
            logging.info(f"Generated emotion guidance: {emotion_guidance}")
            
            input_tokens = self.calculate_total_tokens(detected_emotion, emotion_guidance, relevant_memories, stm_messages)
            logging.info(f"Calculated input_tokens: {input_tokens}")
            
            if input_tokens > MAX_CONTEXT_TOKENS - DigitalCompanion.max_tokens:
                logging.error(f"Token overflow detected: Input exceeds the maximum token limit.")
                raise ValueError("Token overflow detected: Input exceeds the maximum token limit.")

            response = await bound.ainvoke(
                    {
                        "messages": stm_messages,
                        "detected_emotion": detected_emotion,
                        "emotion_prompt": emotion_guidance,
                        "recall_memories": relevant_memories,
                    },
                    config
                )
                
            #print(f"metadata: response.usage_metadata: {response.usage_metadata}")    
            return {"messages": response}
        
        except Exception as e:
            logging.error(f"Error in call_model: {e}")
            # Add context to the exception and re-raise
            raise RuntimeError(f"call_model: Failed to process input for user: {config['configurable'].get('thread_id')}.") from e

    
    ############################################################################################################
    
    async def manage_memory(self, state:MessagesState):
        """
        Manages memory by saving excess messages from short-term memory (STM) to long-term memory (LTM).

        This function checks if the total number of messages exceeds the short-term memory (STM) limit. 
        If so, it saves the oldest messages beyond the STM limit into long-term memory (LTM) while 
        retaining the recent messages within the STM.

        Args:
            state (MessagesState): The current state containing the list of messages.

        Returns:
            None

        Notes:
            - The `stm_limit` attribute defines the maximum number of messages to retain in STM.
            - Messages that exceed the limit are saved to long-term memory (LTM) using `save_to_LTM`.

        """
        try:
            ## Total number of messages in the current state
            total_messages = len(state["messages"])
            logging.info(f"Total messages: {total_messages}")
            
            # Check if the total exceeds the short-term memory limit
            if total_messages > self.stm_limit:
                excess_messages_end = total_messages - self.stm_limit
                messages_to_save = state["messages"][excess_messages_end - 2 : excess_messages_end]
                
                logging.info(f"Messages to save to long-term memory: {messages_to_save}")
                
                await self.save_to_LTM(messages=messages_to_save)
                logging.info(f"Successfully saved {len(messages_to_save)} messages to long-term memory.")
                
        except Exception as e:
            logging.error(f"Error occurred while managing memory: {e}")
            raise
        
    ############################################################################################################    
        
    #def initialize_emotion_detector(self):
        """
        Initialize and return the emotion detector instance.
        """
        #return EmotionDetector() # create and return an instance of the detector
    
    ############################################################################################################
    
    def detect_emotion_tag(self, user_input):
        """
        Detect the primary emotion from the user input and return it as a tag.
        """
        if not DigitalCompanion.emotion_detector:
            raise ValueError("Emotion detector is not initialized.")
        
        emotion_data = DigitalCompanion.emotion_detector.detect_emotion(user_input)
        print(f"Emotion tag: {emotion_data}")
        return emotion_data["primary_emotion"]   # return the primary emotion tag
    
    ############################################################################################################
    
    def generate_emotion_prompt(self, user_input):
        """
        Generate an additional prompt based on the detected emotion.
        """
        try:
            emotion = self.detect_emotion_tag(user_input)
            return emotion, DigitalCompanion.emotion_prompts.get(emotion, "")   ## here we return the prompt based on the emotion
        
        except Exception as e:
            #print(f"Error detecting emotion: {e}")  ## for testing purposes
            return ""
    
    ############################################################################################################
    
    async def stream_workflow_response(self, user_input:str):
        # Replace the input with your user's query
        inputs = [HumanMessage(content=user_input)]
        first = True
        gathered = None

        try:
            logging.info("Starting to stream the response...")
            print("Streaming response:\n"
                  )
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

            logging.info("Streaming completed successfully.")
                

            
        except Exception as e:
            print(f"Error during streaming: {e}")


############################################################################################################
    async def summerize_AI_message(self, message:str):
        
        # Define the summary prompt
        # Define a refined summary prompt
        summary_prompt = (
            "Summarize the following AI message into a concise response."
            "Include only the most important details and specific information. Avoid repeating or expanding the content. "
            "Do not add unnecessary context or embellishments.\n\n"
            "Here is the content to summarize:\n\n"
        )
        
        input_message = [
        HumanMessage(content=summary_prompt + message)
        ]

        # Generate the summary
        summary_message = await DigitalCompanion.model.ainvoke(input_message)

        
        return summary_message.content
    
    ############################################################################################################
    ############################################################################################################
    
    def str_token_counter(self,text: str) -> int:
        """
        Counts the number of tokens in a given text using the model's tokenizer.

        Args:
            text (str): The input text to be tokenized.

        Returns:
            int: The number of tokens in the input text.
        """
        token_ids = self.model.get_token_ids(text)
        
        return len(token_ids)
    
    ############################################################################################################    

    # Token counter function
    def calculate_total_tokens(self, 
                              detected_emotion: str,
                              emotion_prompt: str,
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
        prompt_text = self.build_prompt_text(detected_emotion, emotion_prompt, recall_memories, stm_messages) 
        
        # Count the number of tokens in the prompt text  
        num_tokens = self.str_token_counter(prompt_text)
        
        return num_tokens
    
    ############################################################################################################
    
    def build_prompt_text(
        self, 
        detected_emotion: str, 
        emotion_prompt: str, 
        recall_memories: list[str], 
        stm_messages: list[HumanMessage | AIMessage]
        ) -> str: 
        """
        Builds the final prompt text by filling placeholders in the prompt template.

        Args:
            detected_emotion (str): The detected emotion of the user.
            emotion_prompt (str): The emotion-specific prompt to guide the response.
            recall_memories (list[str]): List of retrieved memories relevant to the conversation.
            stm_messages (list[HumanMessage | AIMessage]): List of short-term memory (STM) messages.

        Returns:
            str: The constructed prompt text with placeholders filled in.

        Raises:
            ValueError: If a required key is missing in the template placeholders.
        """
        try:
            prompt_as_string = self.prompt.format( 
            recall_memories='\n'.join(recall_memories),
            detected_emotion=detected_emotion,
            emotion_prompt=emotion_prompt,
            messages=stm_messages,
            )
        
        except KeyError as e:
            logging.error(f"Missing key in template placeholders:  {e}")
            raise ValueError(f"Missing key in template placeholders: {e}")

        return prompt_as_string
    
############################################################################################################

    async def clear_STM_memories(self):
        """
        Clears all memory for the current user session.

        This method performs two tasks:
        1. Deletes all content from Pinecone under the current user's namespace.
        2. Deletes all messages in the current state for the specified thread/session.

        Returns:
            None
        """
        try:
            # 2. Clear all messages from the state for the current thread
            logging.info(f"Clearing in-memory messages for session: {self.thread_id}")
            # Fetch all messages in the current state
            messages = self.app.get_state(self.config).values["messages"]

            # Delete each message individually
            for message in messages:
                self.app.update_state(self.config, {"messages": RemoveMessage(id=message.id)})
                logging.info(f"Deleted message with ID: {message.id}")

            logging.info(f"Successfully cleared all in-memory messages for session: {self.thread_id}")

        except Exception as e:
            logging.error(f"Error occurred while clearing memory: {e}")
            raise RuntimeError("Failed to clear memory.") from e

