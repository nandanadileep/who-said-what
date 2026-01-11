from collections import defaultdict, Counter
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import HuggingFaceEmbeddings
import numpy as np

from character_config import ALLOWED_CHARACTERS, MAIN_CHARACTERS

INDEX_DIR = "data/index/faiss"
MODEL_NAME = "sentence-transformers/all-mpnet-base-v2"  # Match what you used in build_index


def load_vectorstore():
    embeddings = HuggingFaceEmbeddings(
        model_name=MODEL_NAME,
        model_kwargs={'device': 'cpu'},
        encode_kwargs={'normalize_embeddings': True}
    )
    return FAISS.load_local(
        str(INDEX_DIR),
        embeddings,
        allow_dangerous_deserialization=True
    )


def compute_character_scores_weighted(docs_and_scores, score_method="inverse_distance"):
    """
    Compute character scores from retrieved documents using different weighting schemes.
    
    Args:
        docs_and_scores: List of (document, distance_score) tuples
        score_method: How to weight the scores
            - "inverse_distance": 1 / (distance + epsilon)
            - "exponential": exp(-distance)
            - "rank_based": 1 / rank
            - "reciprocal_rank_fusion": RRF scoring
    """
    scores = defaultdict(float)
    
    for rank, (doc, dist) in enumerate(docs_and_scores):
        char = doc.metadata.get("character")
        
        if char not in ALLOWED_CHARACTERS:
            continue
        
        # Different scoring strategies
        if score_method == "inverse_distance":
            weight = 1 / (dist + 1e-6)
        elif score_method == "exponential":
            weight = np.exp(-dist)
        elif score_method == "rank_based":
            weight = 1 / (rank + 1)
        elif score_method == "reciprocal_rank_fusion":
            # RRF: 1 / (k + rank), k=60 is common
            weight = 1 / (60 + rank)
        else:
            weight = 1 / (dist + 1e-6)
        
        scores[char] += weight
    
    return scores


def compute_character_scores_voting(docs_and_scores, top_k=10):
    """
    Simple majority voting from top-k results.
    """
    votes = Counter()
    
    for doc, _ in docs_and_scores[:top_k]:
        char = doc.metadata.get("character")
        if char in ALLOWED_CHARACTERS:
            votes[char] += 1
    
    # Convert to score dict
    total_votes = sum(votes.values())
    if total_votes == 0:
        return {}

    scores = {char: count / total_votes for char, count in votes.items()}
    
    return scores


def compute_character_scores_mmr(vectorstore, query, docs_and_scores, lambda_param=0.5):
    """
    Maximal Marginal Relevance - balance relevance with diversity.
    Helps avoid retrieving too many similar documents from same character.
    
    This is a simplified version - real MMR would rerank during retrieval.
    """
    scores = defaultdict(float)
    seen_chars = set()
    
    for rank, (doc, dist) in enumerate(docs_and_scores):
        char = doc.metadata.get("character")
        
        if char not in ALLOWED_CHARACTERS:
            continue
        
        # Base relevance score
        relevance = 1 / (dist + 1e-6)
        
        # Diversity penalty if we've seen this character
        diversity = 0 if char in seen_chars else 1
        seen_chars.add(char)
        
        # Combined score
        mmr_score = lambda_param * relevance + (1 - lambda_param) * diversity
        scores[char] += mmr_score
    
    return scores


def predict_character(
    query: str, 
    k: int = 20,
    score_method="inverse_distance",
    min_confidence=0.3
):
    """
    Pure RAG-based character prediction with advanced retrieval techniques.
    
    Args:
        query: The dialogue line to classify
        k: Number of similar documents to retrieve
        score_method: Scoring method (inverse_distance, exponential, rank_based, rrf, voting)
        min_confidence: Minimum confidence threshold to return prediction
    """
    
    vectorstore = load_vectorstore()
    
    # Retrieve similar documents with scores
    docs_and_scores = vectorstore.similarity_search_with_score(query, k=k)
    
    if not docs_and_scores:
        return {
            "prediction": None,
            "confidence": 0.0,
            "reason": "No documents retrieved"
        }
    
    # Compute character scores based on chosen method
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
    
    # Normalize scores for display
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


def compare_scoring_methods(query: str, k: int = 20):
    """
    Compare different scoring methods on the same query.
    Useful for understanding which works best for your data.
    """
    methods = ["inverse_distance", "exponential", "rank_based", "reciprocal_rank_fusion", "voting"]
    
    print(f"\n{'='*70}")
    print(f"Query: '{query}'")
    print(f"{'='*70}\n")
    
    results = {}
    for method in methods:
        result = predict_character(query, k=k, score_method=method)
        results[method] = result
        
        print(f"Method: {method}")
        print(f"  → Prediction: {result['prediction']}")
        print(f"  → Confidence: {result['confidence']:.3f}")
        print(f"  → Top 3 scores: {dict(list(result['all_scores'].items())[:3])}")
        print()
    
    return results


def interactive_mode():
    """Interactive testing mode"""
    print("\n" + "="*70)
    print("RAG Character Prediction - Pure Embedding Approach")
    print("="*70)
    print("\nCommands:")
    print("  - Type a quote to predict character")
    print("  - 'compare <quote>' to compare scoring methods")
    print("  - 'exit' to quit")
    print()
    
    while True:
        user_input = input("🎭 Enter quote: ").strip()
        
        if user_input.lower() == "exit":
            break
        
        if user_input.lower().startswith("compare "):
            query = user_input[8:].strip()
            compare_scoring_methods(query)
            continue
        
        if not user_input:
            continue
        
        # Use best method (you can experiment)
        result = predict_character(
            user_input, 
            k=20, 
            score_method="reciprocal_rank_fusion"  # Generally good default
        )
        
        print(f"\n{'='*70}")
        print(f"🎯 Prediction: {result['prediction']}")
        print(f"📊 Confidence: {result['confidence']:.1%}")
        print(f"⚙️  Method: {result['method']}")
        print(f"\n📈 Score Distribution:")
        for char, score in list(result['all_scores'].items())[:5]:
            bar = "█" * int(score * 50)
            print(f"  {char:20s} {score:.3f} {bar}")
        
        print(f"\n🔍 Top Evidence:")
        for i, ev in enumerate(result['evidence'][:3], 1):
            print(f"\n  {i}. [{ev['character']}] (distance: {ev['distance']})")
            print(f"     {ev['text']}...")
            if 'num_lines' in ev['metadata']:
                print(f"     ({ev['metadata']['num_lines']} lines in chunk)")
        
        print()


if __name__ == "__main__":
    # Quick test
    test_query = "You're in my spot"
    print(f"\n🧪 Testing with: '{test_query}'")
    
    result = predict_character(test_query, k=20, score_method="reciprocal_rank_fusion")
    
    print(f"\n✅ Predicted: {result['prediction']}")
    print(f"📊 Confidence: {result['confidence']:.1%}")
    print(f"\nTop 5 scores: {dict(list(result['all_scores'].items())[:5])}")
    
    print("\n" + "-"*70)
    
    # Start interactive mode
    interactive_mode()