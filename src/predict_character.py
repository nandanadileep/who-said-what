from collections import defaultdict
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings

from character_config import ALLOWED_CHARACTERS, MAIN_CHARACTERS

INDEX_DIR = "data/index/faiss"
MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"


def is_short_query(query: str) -> bool:
    return len(query.strip().split()) <= 3


def load_vectorstore():
    embeddings = HuggingFaceEmbeddings(model_name=MODEL_NAME)
    return FAISS.load_local(
        INDEX_DIR,
        embeddings,
        allow_dangerous_deserialization=True
    )


def predict_character(query: str, k: int = 15):
    vectorstore = load_vectorstore()

    # 1️⃣ Retrieve with scores
    docs_and_scores = vectorstore.similarity_search_with_score(query, k=k)

    # 2️⃣ Filter allowed characters only
    filtered = [
        (doc, dist)
        for doc, dist in docs_and_scores
        if doc.metadata.get("character") in ALLOWED_CHARACTERS
    ]

    if not filtered:
        return {
            "prediction": None,
            "confidence": 0.0,
            "reason": "No valid character evidence found"
        }

    # 3️⃣ Weighted voting
    scores = defaultdict(float)
    evidence = []

    for doc, dist in filtered:
        char = doc.metadata["character"]
        weight = 1 / (dist + 1e-6)

        # 4️⃣ Short-query bias toward main characters
        if is_short_query(query) and char in MAIN_CHARACTERS:
            weight *= 1.5

        scores[char] += weight
        evidence.append((char, doc.page_content))

    # 5️⃣ Final prediction
    predicted = max(scores, key=scores.get)
    total = sum(scores.values())
    confidence = scores[predicted] / total if total > 0 else 0.0

    return {
        "prediction": predicted,
        "confidence": round(confidence, 2),
        "scores": dict(scores),
        "evidence": evidence[:5]
    }


if __name__ == "__main__":
    while True:
        query = input("\nBazinga")
        if query.lower() == "exit":
            break

        result = predict_character(query)

        print("\n🎭 Predicted Character:", result["prediction"])
        print("Confidence:", result["confidence"])
        print("Scores:", result.get("scores"))

        print("\nTop Evidence:")
        for i, (char, text) in enumerate(result["evidence"], 1):
            print(f"{i}. [{char}] {text}")
