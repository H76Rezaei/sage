import uuid
import logging
from typing import List, Union
from langchain_core.messages import AIMessage, HumanMessage
from langgraph.graph import MessagesState
from memory.pinecone_utils import initialize_pinecone, setup_vector_store, get_retriever
from model.summarizer import Summarizer
pc = initialize_pinecone()


class MemoryManager:
    vector_store = None
    summarizer = None
    
    def __init__(self, model, user_id: str, thread_id: str, index_name , embedding_model , embedding_dim , max_results, score_threshold, stm_limit: int = 7):
        """
        Manages long-term and short-term memory for the Digital Companion.

        Args:
            vector_store: The vector store instance for long-term memory.
            retriever: The retriever instance for memory retrieval.
            summarizer: A callable summarizer instance.
            user_id (str): The unique identifier for the user.
            thread_id (str): The current thread or session ID.
            stm_limit (int): The maximum number of messages to retain in short-term memory.
        """
        if not MemoryManager.vector_store:
            MemoryManager.vector_store = setup_vector_store(pc=pc, 
                                                            index_name=index_name, 
                                                            embed_model=embedding_model, 
                                                            embed_dim=embedding_dim)
        #if not MemoryManager.summarizer:
        #    MemoryManager.summarizer = Summarizer(model= model)
                
        self.retriever = get_retriever(MemoryManager.vector_store, max_results=max_results, score_threshold=score_threshold, namespace=user_id)    
        self.user_id = user_id
        self.thread_id = thread_id
        self.stm_limit = stm_limit
        self.is_saved_in_pinecone = False
        

    async def save_to_ltm(self, messages: List[AIMessage | HumanMessage]) -> None:
        """
        Save a list of Human and AI messages to Pinecone as long-term memory (LTM).

        This function combines all the provided messages into a single string, with each message
        prefixed by its type ("Human" for `HumanMessage` and "AI" for `AIMessage`), and stores the
        resulting string in Pinecone under the specified namespace and thread ID.

        Args:
            messages (List[Union[AIMessage, HumanMessage]]): 
                A list of `AIMessage` and `HumanMessage` objects to be saved in long-term memory.

        Returns:
            None
        """
        try:
            combined_messages = []
            for msg in messages:
                if isinstance(msg, HumanMessage):
                    combined_messages.append(f"Human: {msg.content}")
                elif isinstance(msg, AIMessage):
                    # Use the summarizer (callable) to summarize the AI response
                    #summarized_content = await MemoryManager.summarizer.summerize_AI_message(msg.content)
                    combined_messages.append(f"AI: {msg.content}")

            if not combined_messages:
                #logging.warning("No messages to save to long-term memory.")
                return
            
            combined_text = "\n".join(combined_messages)

            await MemoryManager.vector_store.aadd_texts(
                texts=[combined_text],
                namespace=self.user_id,
                metadatas=[{'session_id': self.thread_id}],
                ids=[str(uuid.uuid4())],
            )
            self.is_saved_in_pinecone = True
            #logging.info("Messages saved to long-term memory.")
        
        except Exception as e:
            logging.error(f"Error saving messages to LTM: {e}")
            raise RuntimeError("Failed to save messages to long-term memory.")

    
    async def retrieve_relevant_context(self, query: str) -> List[str]:
        """
        Retrieve relevant long-term memory for the given query.

        Args:
            query (str): The query string to search for.

        Returns:
            List[str]: A list of relevant memories.
        """
        try:
            docs = await self.retriever.ainvoke(query, filter={"session_id": self.thread_id})
            results = [doc.page_content for doc in docs]
            #logging.info(f"Retrieved {len(results)} relevant memories for query: {query}")
            return results
        except Exception as e:
            logging.error(f"Error retrieving context: {e}")
            return []

    
    async def clear_long_term_memory(self) -> None:
        """
        Clear all memories in vectorDB for the user.

        Returns:
            None
        """
        try:
            if self.is_saved_in_pinecone:
                await MemoryManager.vector_store.adelete(delete_all=True, namespace=self.user_id)
                self.is_saved_in_pinecone = False
                logging.info(f"Cleared all long-term memory for user: {self.user_id}.")
        except Exception as e:
            logging.error(f"Error clearing long-term memory: {e}")
            raise RuntimeError("Failed to clear long-term memory.")


    
    async def transfer_excess_to_ltm(self, state:MessagesState):
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
                
                await self.save_to_ltm(messages=messages_to_save)
                logging.info(f"Successfully saved {len(messages_to_save)} messages to long-term memory.")
                
        except Exception as e:
            logging.error(f"Error occurred while managing memory: {e}")
            raise       
    