import time
import logging
from utils.supabase_utils import fetch_parameters, fetch_distinct_conv_ids, fetch_conversations, store_evaluation_results
from companion.evaluation_companion import DigitalCompanion

############################################################################################################

async def process_streaming(handler, conversation, version_id):
    """
    Processes a single conversation using a streaming handler for DigitalCompanion.

    Args:
        user_id (str): The ID of the user interacting with the DigitalCompanion.
        handler (LlamaLocalHandler): The handler for generating responses.
        conversation (list): List of conversation entries for a single `conv_id`.
        version_id (str): The version ID of the DigitalCompanion.

    Returns:
        list: Updated conversation data with responses and timing.
    """
    response_records = []

    for turn in conversation:
        user_input = turn['user_input']
        logging.info(f"Processing turn (streaming): {user_input}")

        response_text = ""
        start_time = time.time()
        first_token_time = None

        # Process the streaming response
        async for token in handler.stream_workflow_response(user_input):
            if first_token_time is None:
                first_token_time = time.time() - start_time  # Time to first token
            response_text += token

        # Calculate the total response time and append results
        full_response_time = time.time() - start_time
        
        """ output_tokens_count = handler.get_output_tokens_count()
        handler.output_tokens_count = None
        logging.info(f'token count: {output_tokens_count}')
        if output_tokens_count == None:
            raise ValueError("No tokens generated in response.") """
        
        response_records.append(
            {
                'log_id': turn['id'],
                'version_id': version_id,
                'generated_response': response_text.strip(),
                'full_response_time': full_response_time,
                'response_time_first_token': first_token_time,
                #'output_tokens_count': output_tokens_count,
            }
        )

    return response_records

############################################################################################################

async def process_and_store_conversations(version_id: int, user_id: str,  thread_id: str):
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
        handler = DigitalCompanion(parameters, user_id= user_id, thread_id=thread_id)        
        
        await handler.memory_manager.clear_long_term_memory()
        logging.info(f'Clearing LTM memories for handler before processing conversations for version ID {version_id}')
        ## Step 3: Fetch distinct conversation IDs
        logging.info("Fetching distinct conversation IDs.")
        conv_ids = fetch_distinct_conv_ids()
        
        ## Step 4: Process each conversation group
        for conv_id in conv_ids:
            logging.info(f"Processing conversation ID {conv_id}")
            conversation_data = fetch_conversations(conv_id)  
             
            response_records = await process_streaming(handler, conversation_data, version_id)
            print('move')
       
            #if hasattr(handler, "clear_memory") and callable(handler.clear_memory):
            logging.info(f"Clearing memory for handler after processing conv_id {conv_id}")
            await handler.clear_all_memories()    ## we should have user_id as input to clear_memory !!!!!
            
            ## Step 7: Store responses in database
            store_evaluation_results(response_records)
    
    except Exception as e:
        logging.error(f"Error processing conversations for version ID {version_id}: {e}")