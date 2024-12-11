import os
import asyncio
import logging
from database.database_utils import fetch_parameters, fetch_distinct_conv_ids, fetch_conversations, store_evaluation_results
from database.handler_factory import get_handler
from database.conversation_processor import _process_streaming, _process_non_streaming

############################################################################################################

def process_and_store_conversations(version_id: int, user_id: str):
    """
    Processes conversations for the given version ID and stores responses in the evaluation table in database.

    Args:
        version_id (int): The version ID to process conversations for.
        user_id (str): The unique identifier for the user (needed for memory handlers).
    """
    try:
        
        ## Step 1: Fetch model parameters and initialize handler
        logging.info(f"Fetching model parameters for version ID {version_id}")
        parameters = fetch_parameters(version_id)
        handler = get_handler(version_id, parameters)        
        
        ## Step 2: Determin if streaming and memory are enabled
        streaming = parameters.get("streaming", False)
        memory_enabled = parameters.get("memory", False)
        
        ## Step 3: Fetch distinct conversation IDs
        logging.info("Fetching distinct conversation IDs.")
        conv_ids = fetch_distinct_conv_ids()
        
        ## Step 4: Process each conversation group
        for conv_id in conv_ids:
            logging.info(f"Processing conversation ID {conv_id}")
            conversation_data = fetch_conversations(conv_id)  
        
            ## Step 5: Generate responses
            if streaming:
                
                response_records = asyncio.run(_process_streaming(user_id, handler, conversation_data, version_id))
                print('move')
            else:
                response_records = _process_non_streaming(handler, conversation_data, version_id)
            
            ## Step 6: Clear memory if enabled
            if memory_enabled:
                #if hasattr(handler, "clear_memory") and callable(handler.clear_memory):
                logging.info(f"Clearing memory for handler after processing conv_id {conv_id}")
                handler.clear_memory(user_id)    ## we should have user_id as input to clear_memory !!!!!
            
            ## Step 7: Store responses in database
            store_evaluation_results(response_records)
    
    except Exception as e:
        logging.error(f"Error processing conversations for version ID {version_id}: {e}")

############################################################################################################

if __name__ == "__main__":
    user_id = "test_user"
    process_and_store_conversations(4, user_id)



 
            



