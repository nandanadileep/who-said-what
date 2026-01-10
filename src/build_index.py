from pathlib import Path
import pickle

from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS

DOCS_PATH = Path("data/processed/documents.pkl")
INDEX_DIR = Path("data/index/faiss")


def main():
    with open(DOCS_PATH, "rb") as f:
        documents = pickle.load(f)

    print(f"Loaded {len(documents)} documents")

    embeddings = HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2"
    )

    vectorstore = FAISS.from_documents(
        documents=documents,
        embedding=embeddings
    )

    INDEX_DIR.mkdir(parents=True, exist_ok=True)
    vectorstore.save_local(str(INDEX_DIR))

    print("AISS index built and saved")
    print(f"Index location: {INDEX_DIR}")


if __name__ == "__main__":
    main()
