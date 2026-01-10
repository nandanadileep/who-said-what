import pandas as pd
from pathlib import Path
from langchain_core.documents import Document
import pickle

DATA_PATH = Path("data/processed/dialogues.csv")
OUT_PATH = Path("data/processed/documents.pkl")


def main():
    df = pd.read_csv(DATA_PATH)

    documents = []

    for _, row in df.iterrows():
        doc = Document(
            page_content=row["text"],
            metadata={
                "character": row["character"]
            }
        )
        documents.append(doc)

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_PATH, "wb") as f:
        pickle.dump(documents, f)

    print("Document creation complete")
    print(f"Total documents created: {len(documents)}")
    print(f"Saved to: {OUT_PATH}")


if __name__ == "__main__":
    main()
