import time
import logging
from handler_classes.llama_local_handler import LlamaLocalHandler
############################################################################################################

async def unified_generate_response_streaming(user_id, handler, user_input):
    """
    Unified interface for streaming response generation.

    Args:
        handler (ModelHandlerBase): The handler instance.
        user_input (_type_): _description_

    Returns:
        tuple: Token and wheter it is the final token.
    
    """
    if isinstance(handler, LlamaLocalHandler):
        response_text = ""
        async for token in handler.generate_response_streaming(user_id,user_input):
            response_text += token
            yield token, False
        yield response_text, True
    
    else:
        
        async for token, is_final in handler.generate_response_streaming(user_input):
            yield token, is_final
############################################################################################################

async def _process_streaming(user_id, handler, conversation, version_id):
    """
    Processes a single conversation using a streaming handler.

    Args:
        handler (ModelHandlerBase): The handler for generating responses.
        conversation (list): List of conversation entries for a single `conv_id`.

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

        # Use the unified wrapper for consistent interface
        async for token, is_final in unified_generate_response_streaming(user_id, handler, user_input):
            if first_token_time is None:
                first_token_time = time.time() - start_time  # Time to first token
            response_text += token

            if is_final:
                
                full_response_time = time.time() - start_time
                response_records.append(
                    {
                        'log_id': turn['id'],
                        'version_id': version_id,
                        'generated_response': response_text.strip(),
                        'full_response_time': full_response_time,
                        'response_time_first_token': first_token_time,
                    }
                )
                
                break

    return response_records

        
############################################################################################################
        
def _process_non_streaming(handler, conversation, version_id):
    """
    Processes a single conversation using a non-streaming handler.

    Args:
        handler (ModelHandlerBase): The handler for generating responses.
        conversation (list): List of conversation entries.

    Returns:
        list: Updated conversation data with responses and timing.
    """
    response_records = []
    for turn in conversation:
        user_input = turn['user_input']
        logging.info(f"Processing turn (non-streaming): {user_input}")

        start_time = time.time()
        bot_response = handler.generate_response(user_input)
        full_response_time = time.time() - start_time

        response_records.append(
            {
                'log_id': turn['id'],
                'version_id': version_id,
                'generated_response': bot_response.strip(),
                'full_response_time': full_response_time,
                'response_time_first_token': None,  # Not applicable for non-streaming
            }
        )

    return response_records
