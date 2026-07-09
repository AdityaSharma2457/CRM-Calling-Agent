import os
import logging
import requests
import chromadb
from chromadb.api.types import Documents, EmbeddingFunction, Embeddings
from app.config import settings

logger = logging.getLogger(__name__)

class HuggingFaceBgem3EmbeddingFunction(EmbeddingFunction):
    """
    Custom Chroma Embedding Function that queries the free Hugging Face Inference API
    for BAAI/bge-m3 embeddings to perform semantic search.
    """
    def __init__(self, api_key: str = ""):
        self.api_key = api_key
        self.url = "https://api-inference.huggingface.co/pipeline/feature-extraction/BAAI/bge-m3"

    def __call__(self, input: Documents) -> Embeddings:
        headers = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        
        try:
            response = requests.post(self.url, headers=headers, json={"inputs": input})
            response.raise_for_status()
            embeddings = response.json()
            
            # Hugging Face feature-extraction returns a list of floats for a single text,
            # and a list of lists of floats for multiple texts.
            if isinstance(embeddings, list) and len(embeddings) > 0:
                if isinstance(embeddings[0], float):
                    return [embeddings]
                return embeddings
            else:
                raise ValueError("Unexpected response format from Hugging Face embeddings API")
        except Exception as e:
            logger.exception("Failed to get embeddings from Hugging Face")
            # Fallback to zero-vector of length 1024 (dimension of BGE-M3) to prevent crashes
            logger.warning("Using zero embeddings fallback.")
            return [[0.0] * 1024 for _ in input]


# Resolve paths
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
FALLBACK_KB_FILE = os.path.join(CURRENT_DIR, "university_info.txt")

# Global variables for Chroma client and collection
chroma_client = None
collection = None

def init_chroma():
    global chroma_client, collection
    if chroma_client is not None:
        return
        
    try:
        # Ensure path directory exists
        os.makedirs(settings.CHROMA_DB_PATH, exist_ok=True)
        
        # Initialize persistent client
        chroma_client = chromadb.PersistentClient(path=settings.CHROMA_DB_PATH)
        
        embedding_fn = HuggingFaceBgem3EmbeddingFunction(api_key=settings.HF_API_KEY)
        collection = chroma_client.get_or_create_collection(
            name=settings.CHROMA_COLLECTION_NAME,
            embedding_function=embedding_fn
        )
        logger.info(f"Chroma DB client initialized. Collection: {settings.CHROMA_COLLECTION_NAME}")
    except Exception as e:
        logger.exception("Failed to initialize Chroma DB client")

def get_relevant_context(query: str, n_results: int = 3) -> str:
    """Queries the Chroma DB collection to retrieve matching chunks for RAG."""
    init_chroma()
    
    if collection is None:
        logger.error("Chroma DB collection not initialized. Falling back to local file.")
        return get_fallback_context()

    try:
        # Query Chroma DB
        results = collection.query(
            query_texts=[query],
            n_results=n_results
        )
        
        # Check if we got results
        documents = results.get("documents", [[]])[0]
        if documents:
            logger.info(f"Successfully retrieved {len(documents)} matching chunks from Chroma DB.")
            return "\n\n".join(documents)
            
    except Exception as e:
        logger.error(f"Error querying Chroma DB: {e}")
        
    # Fallback to local text file if DB is empty/fails
    logger.warning("Falling back to local text file content.")
    return get_fallback_context()

def get_fallback_context() -> str:
    """Helper to return the default university info text file content."""
    if os.path.exists(FALLBACK_KB_FILE):
        try:
            with open(FALLBACK_KB_FILE, "r", encoding="utf-8") as f:
                return f.read().strip()
        except Exception:
            pass
    return "No university information database is currently available."
