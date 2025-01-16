import logging
from dotenv import load_dotenv
load_dotenv()

import os
from supabase import create_client

## configure logging
logging.basicConfig(level=logging.INFO)

## Connect to Supabase
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")

supabase = create_client(url, key)


def fetch_prompt_data(system_id=5, emotion_group_id=5):
    """
    Fetches the system and emotion prompts for the given system_id and emotion_id from the database.
    
    Args:
        system_id (int): The system_id for which to fetch the system prompt.
        emotion_group_id (int): The emotion_id for which to fetch the emotion prompts.
        
    Returns:
        str: The system prompt text.
        dict: A dictionary containing emotion prompts for each emotion.
    """
    
    system_prompt_data = supabase.table('system_prompts').select("prompt_text").eq("id", system_id).execute()
    system_prompt = system_prompt_data.data[0].get('prompt_text')
    emotion_data = supabase.table('emotion_prompts').select("emotion", "prompt_text").eq("group_id", emotion_group_id).execute()
    emotion_prompts = {dict['emotion']: dict['prompt_text'] for dict in emotion_data.data}
    
    return system_prompt, emotion_prompts

############################################################################################################

def fetch_parameters(version_id: int) -> dict:
    """
    Fetches the parameters for the giveen version_id from the database.
    
    Args:
        version_id (int): The version_id for which to fetch the parameters.
        
    Returns:
        dict: A dictionary containing all parameters for the given version_id.
    """
    ## Fetch version data
    version_data = supabase.table('versions').select('*').eq('id', version_id).execute()
    
    if not version_data.data:
        raise ValueError(f"Version with id {version_id} not found in the database.")
    
    ## Extract parameters
    parameters = version_data.data[0]  ## dictionary
    
    ## Fetch system prompt
    system_prompt_id = parameters.get('system_prompt_id')
    if system_prompt_id:
        system_prompt_data = supabase.table('system_prompts').select("prompt_text").eq("id", system_prompt_id).execute()
        parameters["system_prompt"] = system_prompt_data.data[0]["prompt_text"]
        
    ## Fetch emotion prompts
    emotion_prompt_group_id = parameters.get('emotion_prompt_id')
    if emotion_prompt_group_id:
        emotion_prompts_data = supabase.table('emotion_prompts').select("emotion", "prompt_text").eq("group_id", emotion_prompt_group_id).execute()
        parameters["emotion_prompts"] = {
            item['emotion']: item['prompt_text'] for item in emotion_prompts_data.data
            } if emotion_prompts_data.data else None
    
    return parameters

############################################################################################################
        
def fetch_distinct_conv_ids():
    """
    Fetches distinct conversation IDs from the `conversation_logs` table.

    Returns:
        list: A sorted list of distinct conversation IDs.
    """
    conv_ids_DB = supabase.rpc('distinct_values', {
        'column_name': 'conv_id',
        'table_name': 'conversation_logs'
    }).execute()

    if not conv_ids_DB.data:
        logging.warning("No conversation IDs found in the database.")
        return []

    conv_ids = sorted([int(conv['value']) for conv in conv_ids_DB.data])
    logging.info(f"Fetched {len(conv_ids)} conversation IDs.")
    return conv_ids

############################################################################################################
                
def fetch_conversations(conv_id: int):
    """
    Fetches all user inputs for the given conversation ID from the `conversation_logs` table.
    
    Args:
        conv_id (int): The conversation ID for which to fetch the user inputs.
        
    Returns:
        list: A list of dictionaries containing the user inputs for the given conversation ID.
    """
    conversation = supabase.table('conversation_logs').select('id','user_input').eq("conv_id", conv_id).execute()
    
    if not conversation.data:
        logging.warning(f"No user inputs found for conversation ID {conv_id}.")
        return []
    
    conv_data = conversation.data
    logging.info(f"Fetched {len(conv_data)} user inputs for conversation ID {conv_id}.")
    return conv_data

############################################################################################################

def store_evaluation_results(response_records: list):
    """
    Stores the response records in the evaluation table.

    Args:
        response_records (list): A list of dictionaries containing response data.
            Each dictionary should have the keys:
                - 'log_id': ID of the log in the conversation_logs table.
                - 'version_id': ID of the version being evaluated.
                - 'generated_response': The generated response.
                - 'full_response_time': Total time taken for the full response.
                - 'response_time_first_token': Time taken for the first token.
                - 'output_tokens_count': Number of tokens in the generated response.
    """
    if not response_records:
        logging.warning("No response records provided for storage.")
        return
    
    
    logging.info("Storing evaluation results in the database...")
    for record in response_records:
        try:
            result = supabase.table('evaluation').insert(record).execute()
            
            if not result.data:
                logging.error(f"Failed to store evaluation record for log ID {record['log_id']}.")
            else:
                logging.info(f"Successfully stored evaluation record for log_id {record['log_id']}.")
        
        except Exception as e:
            logging.error(f"Error storing evaluation record for log ID {record['log_id']}: {str(e)}")
            
            


