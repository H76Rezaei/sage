import logging
from database.database_utils import fetch_parameters
from handler_classes.base_handler import ModelHandlerBase
from handler_classes.blenderbot_handler import BlenderBotHandler
from handler_classes.llama_local_handler import LlamaLocalHandler
from handler_classes.llama_cloud_handler import LlamaCloudHandler

# Configure logging
logging.basicConfig(level=logging.INFO)

HANDLER_MAPPING = {
    "facebook/blenderbot-400M-distill": BlenderBotHandler,
    "meta-llama/Llama-3.2-1B-Instruct": LlamaCloudHandler,
    "llama3.2:1b": LlamaLocalHandler,
}


def get_handler(version_id: int, parameters:dict) -> ModelHandlerBase:
    """
    Factory to create a handler based on the version_id.
    
    Args:
        version_id (int): The version_id for which to create a handler.
        
    Returns:
        ModelHandlerBase: An instance of the appropriate model handler.   
    """
    
    logging.info(F"Fetching parameters for version_id {version_id}")
    try:
        #parameters = fetch_parameters(version_id)
        model_name = parameters.get("model_name")

        if not model_name:
            logging.error(f"Model name not found in parameters for version_id {version_id}")
            raise ValueError(f"Model name not found in parameters for version_id {version_id}")

        handler_class = HANDLER_MAPPING.get(model_name)
        if not handler_class:
            logging.error(f"Model name {model_name} not supported for version_id {version_id}.")
            raise ValueError(f"Model name {model_name} not supported.")
        
        logging.info(f"Creating handler for version_id {version_id} with model name {model_name}")

        return handler_class(parameters)
    
    except Exception as e:
        logging.error(f"Error creating handler for version_id {version_id}: {str(e)}")
        raise 
    
    
    

    
    
    