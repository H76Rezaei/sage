## utils.py

from pinecone import Pinecone, ServerlessSpec
from langchain_pinecone import PineconeVectorStore
from langchain_huggingface import HuggingFaceEmbeddings
from dotenv import load_dotenv
import logging
import os
import time
import os
from dotenv import load_dotenv
from pinecone import Pinecone

logging.basicConfig(level=logging.INFO)
####################################################################################################
def initialize_pinecone() -> Pinecone:
    """
    Initializes Pinecone using the API key from environment variables.
    
    Returns:
        Pinecone: The initialized Pinecone object.
    """
    # Load environment variables (only once per script execution)
    load_dotenv()
    
    # Fetch the Pinecone API key
    pinecone_api_key = os.environ.get("PINECONE_API_KEY")
    if not pinecone_api_key:
        raise ValueError("Pinecone API key not found. Set PINECONE_API_KEY in the environment.")
    
    pc = Pinecone(api_key=pinecone_api_key)
    logging.info("Pinecone initialized successfully.")
    
    return pc

####################################################################################################
def get_pinocone_index(pc: Pinecone, index_name, dimension, metric="cosine"):
    """
    Creates a Pinecone index if it doesn't already exist.

    Args:
        index_name (str): The name of the index.
        dimension (int): The dimension of the embeddings.
        metric (str): The similarity metric to use (e.g., 'cosine').
    """
    
    ## Retrieves a list of all existing indexes in your Pinecone account.
    existing_indexes = [index_info['name'] for index_info in pc.list_indexes()]  
    if index_name not in existing_indexes:
        pc.create_index(
            name=index_name,
            dimension=dimension,
            metric=metric,
            spec=ServerlessSpec(
            cloud="aws",
            region="us-east-1"
        )
            
        )
        while not pc.describe_index(index_name).status['ready']:
            logging.info(f"Waiting for Pinecone index '{index_name}' to be ready...")
            time.sleep(1)

    index = pc.Index(index_name)
    logging.info(f"Pinecone index '{index_name}' is ready.")
    return index
   
####################################################################################################

def setup_vector_store(pc: Pinecone, index_name="chatbot-memory", embed_model="intfloat/multilingual-e5-large", embed_dim=1024):
    """
    Initializes the vector store with the specified Pinecone index and embedding model.

    Args:
        index_name (str): The name of the Pinecone index.
        embed_model (str): The name of the embedding model.
        embed_dim (int): The dimension of the embeddings.

    Returns:
        PineconeVectorStore: The initialized vector store.
    """
    index = get_pinocone_index(pc=pc, index_name=index_name, dimension=embed_dim)
    
    ## Set up the embeddings
    embeddings = HuggingFaceEmbeddings(model_name=embed_model)
    
    ## Create the vector store
    vector_store = PineconeVectorStore(index, embeddings)
    logging.info(f"Vector store initialized with Pinecone index '{index_name}'.")

    return vector_store
    

####################################################################################################

def get_retriever(vector_store, max_results , score_threshold, namespace):
    
        retriever = vector_store.as_retriever(
            search_type="similarity_score_threshold",
            search_kwargs={
                "k": max_results,  # Retrieve up to 3 results
                "score_threshold": score_threshold,  # Only include results with similarity >= 0.8
                "namespace": namespace
            }
        ) 
        return retriever