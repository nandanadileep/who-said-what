from collections import defaultdict, Counter
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import HuggingFaceEmbeddings
import numpy as np

from character_config import ALLOWED_CHARACTERS, MAIN_CHARACTERS

INDEX_DIR = "data/index/faiss"
MODEL_NAME = "sentence-transformers/all-mpnet-base-v2"

# Global cache to avoid reloading model on every request
_cached_vectorstore = None


def load_vectorstore():
    """Load vectorstore once and cache it globally."""
    global _cached_vectorstore
    
    if _cached_vectorstore is not None:
        return _cached_vectorstore
    
    print(f"Loading embedding model: {MODEL_NAME}")
    embeddings = HuggingFaceEmbeddings(
        model_name=MODEL_NAME,
        model_kwargs={'device': 'cpu'},
        encode_kwargs={'normalize_embeddings': True}
    )
    
    print(f"Loading FAISS index from: {INDEX_DIR}")
    _cached_vectorstore = FAISS.load_local(
        str(INDEX_DIR),
        embeddings,
        allow_dangerous_deserialization=True
    )
    
    print("✓ Vectorstore loaded and cached")
    return _cached_vectorstore


def compute_character_scores_weighted(docs_and_scores, score_method="inverse_distance"):
    """Compute character scores from retrieved documents."""
    scores = defaultdict(float)
    
    for rank, (doc, dist) in enumerate(docs_and_scores):
        char = doc.metadata.get("character")
        
        if char not in ALLOWED_CHARACTERS:
            continue
        
        if score_method == "inverse_distance":
            weight = 1 / (dist + 1e-6)
        elif score_method == "exponential":
            weight = np.exp(-dist)
        elif score_method == "rank_based":
            weight = 1 / (rank + 1)
        elif score_method == "reciprocal_rank_fusion":
            weight = 1 / (60 + rank)
        else:
            weight = 1 / (dist + 1e-6)
        
        scores[char] += weight
    
    return scores


def compute_character_scores_voting(docs_and_scores, top_k=10):
    """Simple majority voting from top-k results."""
    votes = Counter()
    
    for doc, _ in docs_and_scores[:top_k]:
        char = doc.metadata.get("character")
        if char in ALLOWED_CHARACTERS:
            votes[char] += 1
    
    total_votes = sum(votes.values())
    if total_votes == 0:
        return {}

    scores = {char: count / total_votes for char, count in votes.items()}
    return scores


def predict_character(
    query: str, 
    k: int = 20,
    score_method="inverse_distance",
    min_confidence=0.25
):
    """
    Pure RAG-based character prediction.
    
    Args:
        query: The dialogue line to classify
        k: Number of similar documents to retrieve
        score_method: Scoring method
        min_confidence: Minimum confidence threshold
    """
    
    vectorstore = load_vectorstore()
    
    # Retrieve similar documents
    docs_and_scores = vectorstore.similarity_search_with_score(query, k=k)
    
    if not docs_and_scores:
        return {
            "prediction": None,
            "confidence": 0.0,
            "reason": "No documents retrieved"
        }
    
    # Compute scores
    if score_method == "voting":
        scores = compute_character_scores_voting(docs_and_scores, top_k=k)
    else:
        scores = compute_character_scores_weighted(docs_and_scores, score_method)
    
    if not scores:
        return {
            "prediction": None,
            "confidence": 0.0,
            "reason": "No valid characters in results"
        }
    
    # Get prediction
    predicted_char = max(scores, key=scores.get)
    total_score = sum(scores.values())
    confidence = scores[predicted_char] / total_score if total_score > 0 else 0.0
    
    # Collect evidence
    evidence = []
    for doc, dist in docs_and_scores[:5]:
        char = doc.metadata.get("character")
        if char in ALLOWED_CHARACTERS:
            evidence.append({
                "character": char,
                "text": doc.page_content[:150],
                "distance": round(float(dist), 4),
                "metadata": doc.metadata
            })
    
    # Normalize scores
    normalized_scores = {
        char: round(score / total_score, 3) 
        for char, score in sorted(scores.items(), key=lambda x: x[1], reverse=True)
    }
    
    result = {
        "prediction": predicted_char if confidence >= min_confidence else None,
        "confidence": round(confidence, 3),
        "all_scores": normalized_scores,
        "evidence": evidence,
        "method": score_method,
        "num_retrieved": len(docs_and_scores)
    }
    
    if confidence < min_confidence:
        result["reason"] = f"Confidence {confidence:.3f} below threshold {min_confidence}"
    
    return result