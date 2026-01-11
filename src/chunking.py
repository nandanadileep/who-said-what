import pandas as pd
from pathlib import Path
from langchain_core.documents import Document
import pickle

DATA_PATH = Path("data/processed/dialogues.csv")
OUT_PATH = Path("data/processed/documents.pkl")


def create_chunked_documents(df, chunk_size=10, overlap=3):

    documents = []
    
    for character in df['character'].unique():
        char_df = df[df['character'] == character].reset_index(drop=True)
        
        for i in range(0, len(char_df), chunk_size - overlap):
            chunk = char_df.iloc[i:i + chunk_size]
            
            if len(chunk) == 0:
                continue
            
            combined_text = " ".join(chunk['text'].values)
            
            doc = Document(
                page_content=combined_text,
                metadata={
                    "character": character,
                    "num_lines": len(chunk),
                    "start_idx": i
                }
            )
            documents.append(doc)
    
    return documents


def create_contextual_documents(df, window_size=5):
    documents = []
    
    for character in df['character'].unique():
        char_df = df[df['character'] == character].reset_index(drop=True)
        
        for idx, row in char_df.iterrows():
            start_idx = max(0, idx - window_size)
            end_idx = min(len(char_df), idx + window_size + 1)
            
            context_lines = char_df.iloc[start_idx:end_idx]['text'].tolist()
            
            main_text = row['text']
            context_text = " ".join(context_lines)
            
            combined_text = f"{main_text} {context_text}"
            
            doc = Document(
                page_content=combined_text,
                metadata={
                    "character": character,
                    "main_line": main_text,
                    "context_size": len(context_lines)
                }
            )
            documents.append(doc)
    
    return documents


def main():
    df = pd.read_csv(DATA_PATH)
    
    print(f"Loaded {len(df)} dialogue lines")
    print(f"Characters: {df['character'].nunique()}")
    
    # Strategy 1: Chunked (better for general character voice)
    documents = create_chunked_documents(df, chunk_size=15, overlap=5)
    
    # Strategy 2: Contextual (better for specific line matching)
    # documents = create_contextual_documents(df, window_size=5)
    
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_PATH, "wb") as f:
        pickle.dump(documents, f)
    
    print(f"\n✅ Document creation complete")
    print(f"Total documents created: {len(documents)}")
    print(f"Saved to: {OUT_PATH}")
    
    # Show sample
    print(f"\n📝 Sample document:")
    sample = documents[0]
    print(f"Character: {sample.metadata['character']}")
    print(f"Content: {sample.page_content[:200]}...")
    print(f"Metadata: {sample.metadata}")


if __name__ == "__main__":
    main()