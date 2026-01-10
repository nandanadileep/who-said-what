from collections import defaultdict
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings

from character_config import MAIN_CHARACTERS, ALLOWED_CHARACTERS
from catchphrases import CATCHPHRASES

INDEX_DIR = "data/index/faiss"
MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"


def is_short_query(query: str) -> bool:
    return len(query.strip().split()) <= 3

def check_catchphrase(query: str):
    q = query.lower().strip()
    for phrase, info in CATCHPHRASES.items():
        if phrase in q:
            return {
                "prediction": info["character"],
                "confidence": info["confidence"],
                "reason": "catchphrase_match",
                "scores": {info["character"]: info["confidence"]},
                "evidence": [(info["character"], phrase)]
            }
    return None

def load_vectorstore():
    embeddings = HuggingFaceEmbeddings(model_name=MODEL_NAME)
    return FAISS.load_local(
        INDEX_DIR,
        embeddings,
        allow_dangerous_deserialization=True
    )


def predict_character(query: str, k: int = 15):
    override = check_catchphrase(query)
    if override:
        return override
    vectorstore = load_vectorstore()

    docs_and_scores = vectorstore.similarity_search_with_score(query, k=k)

    filtered = [
        (doc, dist)
        for doc, dist in docs_and_scores
        if doc.metadata.get("character") in ALLOWED_CHARACTERS
    ]

    if not filtered:
        return {"prediction": None, "confidence": 0.0}

    scores = defaultdict(float)
    evidence = []

    for doc, dist in filtered:
        char = doc.metadata["character"]
        weight = 1 / (dist + 1e-6)

        if is_short_query(query) and char in MAIN_CHARACTERS:
            weight *= 1.5

        scores[char] += weight
        evidence.append((char, doc.page_content))

    predicted = max(scores, key=scores.get)
    total = sum(scores.values())
    confidence = scores[predicted] / total if total else 0.0

    return {
        "prediction": predicted,
        "confidence": round(confidence, 2),
        "scores": dict(scores),
        "evidence": evidence[:5]
    }


if __name__ == "__main__":
    while True:
        query = input("You’re in my spot")
        if query.lower() == "exit":
            break

        result = predict_character(query)

        print("\n🎭 Predicted Character:", result["prediction"])
        print("Confidence:", result["confidence"])
        print("Scores:", result["scores"])

        print("\nTop Evidence:")
        for i, (char, text) in enumerate(result["evidence"], 1):
            print(f"{i}. [{char}] {text}")
