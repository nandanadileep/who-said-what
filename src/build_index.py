from pathlib import Path
import pickle

from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS

DOCS_PATH = Path("data/processed/documents.pkl")
INDEX_DIR = Path("data/index/faiss")

# Better embedding models to try (in order of quality vs speed):
EMBEDDING_MODELS = {
    "mini": "sentence-transformers/all-MiniLM-L6-v2",  # Fast, 384 dim
    "mpnet": "sentence-transformers/all-mpnet-base-v2",  # Better, 768 dim  
    "e5": "intfloat/e5-base-v2",  # Good for semantic search, 768 dim
    "instructor": "hkunlp/instructor-base",  # Task-specific, 768 dim
}


def main(model_key="mpnet"):
    """
    Build FAISS index with better embedding model.
    
    Args:
        model_key: Which embedding model to use (mini, mpnet, e5, instructor)
    """
    
    with open(DOCS_PATH, "rb") as f:
        documents = pickle.load(f)
    
    print(f"📚 Loaded {len(documents)} documents")
    
    model_name = EMBEDDING_MODELS[model_key]
    print(f"🤖 Using embedding model: {model_name}")
    
    # Initialize embeddings
    # Note: all-mpnet-base-v2 is generally better than all-MiniLM-L6-v2
    # for semantic similarity tasks
    embeddings = HuggingFaceEmbeddings(
        model_name=model_name,
        model_kwargs={'device': 'cpu'},  # Use 'cuda' if you have GPU
        encode_kwargs={'normalize_embeddings': True}  # Important for cosine similarity
    )
    
    print("🔨 Building FAISS index...")
    
    # Create vector store
    vectorstore = FAISS.from_documents(
        documents=documents,
        embedding=embeddings
    )
    
    # Save index
    INDEX_DIR.mkdir(parents=True, exist_ok=True)
    vectorstore.save_local(str(INDEX_DIR))
    
    print(f"✅ FAISS index built and saved")
    print(f"📍 Index location: {INDEX_DIR}")
    
    # Quick test
    print("\n🧪 Testing index with sample query...")
    test_query = "You're in my spot"
    results = vectorstore.similarity_search_with_score(test_query, k=5)
    
    print(f"\nQuery: '{test_query}'")
    print("\nTop 5 results:")
    for i, (doc, score) in enumerate(results, 1):
        char = doc.metadata.get('character', 'Unknown')
        text_preview = doc.page_content[:100]
        print(f"{i}. [{char}] (score: {score:.4f})")
        print(f"   {text_preview}...")
        print()


if __name__ == "__main__":
    # Use mpnet for better quality, or mini for faster performance
    main(model_key="mpnet")