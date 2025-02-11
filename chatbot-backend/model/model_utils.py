
from langchain_ollama  import ChatOllama
import torch
import json
import logging
####################################################################################################
def init_model(
    model,
    temperature,
    max_tokens,
    top_p,
    device,
    stream
):
    """
    Initialize and return the model instance.

    Args:
        model_name (str): The name of the model to use.
        temperature (float): Sampling temperature for the model.
        max_tokens (int): Maximum tokens for the model output.
        top_p (float): Nucleus sampling parameter.
        device (str, optional): Device to use ('cuda', 'cpu'). If None, it is detected automatically.

    Returns:
        ChatOllama: The initialized shared model.
    """
    if device is None:
        device = "cuda" if torch.cuda.is_available() else "mps" if torch.backends.mps.is_available() else "cpu"
        
    #logging.info(f"Using device: {device}")
    
    model = ChatOllama(
        model=model,
        temperature=temperature,
        num_predict=max_tokens,
        top_p=top_p,
        device=device,
        stream=stream
    )
    return model

####################################################################################################

def load_json_config(path):
    """
    Load the default configuration from the JSON file.
    Returns:
    dict: The default configuration dictionary.
    """
    with open(path, "r") as file:
        return json.load(file)
