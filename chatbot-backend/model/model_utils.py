
from langchain_ollama  import ChatOllama
import torch
import json
import logging
from dotenv import load_dotenv
import os
from langchain_huggingface import ChatHuggingFace, HuggingFaceEndpoint
####################################################################################################

# Load environment variables from .env file
load_dotenv()

def init_model(
    model,           # now this should be the repo ID of the Hugging Face model (e.g., "HuggingFaceH4/zephyr-7b-beta")
    temperature,     
    max_tokens,      # will be passed as max_new_tokens
    top_p,
    device,          # may not be used by the Hugging Face cloud endpoint
    stream
):
    """
    Initialize and return the Hugging Face cloud model instance.

    Args:
        model (str): The Hugging Face repo ID of the model to use.
        temperature (float): Sampling temperature.
        max_tokens (int): Maximum new tokens for generation.
        top_p (float): Nucleus sampling parameter.
        device (str): Device string (not used here, as the cloud model runs remotely).
        stream (bool): Whether to use streaming responses (if supported).

    Returns:
        ChatHuggingFace: The initialized model wrapped in a ChatHuggingFace interface.
    """

    # Get API key from environment variable
    api_key = os.getenv("HUGGINGFACE_TOKEN")

    if not api_key:
        raise ValueError("Hugging Face API key is missing! Please set HUGGINGFACE_TOKEN in your .env file.")

    
    logging.info(f"Using Hugging Face model: {model}")

    if device is None:
        device = "cuda" if torch.cuda.is_available() else "mps" if torch.backends.mps.is_available() else "cpu"
        
    logging.info(f"Using device: {device}")
    
    # Create a HuggingFaceEndpoint instance.
    # You may adjust the task and additional parameters as needed.
    llm = HuggingFaceEndpoint(
        repo_id=model,
        task="text-generation",  # Adjust if you need a different task
        max_new_tokens=max_tokens,
        do_sample=(temperature > 0),  # Enable sampling if temperature > 0
        temperature=temperature,
        top_p=top_p,
        huggingfacehub_api_token=api_key
    )
    
    
    # Wrap the endpoint with ChatHuggingFace.
    chat_model = ChatHuggingFace(llm=llm)
    return chat_model

#ollama initiator
"""
def init_model(
    model,
    temperature,
    max_tokens,
    top_p,
    device,
    stream
):
    """
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
"""
    if device is None:
        device = "cuda" if torch.cuda.is_available() else "mps" if torch.backends.mps.is_available() else "cpu"
        
    logging.info(f"Using device: {device}")
    
    model = ChatOllama(
        model=model,
        temperature=temperature,
        num_predict=max_tokens,
        top_p=top_p,
        device=device,
        stream=stream
    )
    return model
"""

####################################################################################################

def load_json_config(path):
    """
    Load the default configuration from the JSON file.
    Returns:
    dict: The default configuration dictionary.
    """
    with open(path, "r") as file:
        return json.load(file)