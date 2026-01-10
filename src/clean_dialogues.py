import pandas as pd
import re
from pathlib import Path

from character_normalisation import normalize_character

RAW_PATH = Path("data/raw/1_10_seasons_tbbt.csv")
OUT_PATH = Path("data/processed/dialogues.csv")


def clean_dialogue_text(text: str):
    if not isinstance(text, str):
        return None

    text = re.sub(r"\(.*?\)", "", text)
    text = re.sub(r"\[.*?\]", "", text)
    text = re.sub(r"\s+", " ", text).strip()

    return text if text else None


def is_low_information(text: str) -> bool:
    if not isinstance(text, str):
        return True

    tokens = text.lower().split()

    if len(tokens) < 3:
        return True

    fillers = {
        "uh", "um", "yeah", "okay", "ok", "oh", "hmm", "huh"
    }

    return all(t.strip(".,!?…") in fillers for t in tokens)


def main():
    df = pd.read_csv(RAW_PATH)

    # Keep only spoken lines
    df = df[df["person_scene"] != "Scene"].copy()

    df.rename(
        columns={
            "person_scene": "character",
            "dialogue": "text"
        },
        inplace=True
    )

    df["text"] = df["text"].apply(clean_dialogue_text)
    df["character"] = df["character"].apply(normalize_character)

    df.dropna(subset=["text", "character"], inplace=True)
    df = df[~df["text"].apply(is_low_information)]

    df = df[["character", "text"]].reset_index(drop=True)

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT_PATH, index=False)

    print(f"✅ Cleaned dataset saved: {len(df)} rows")


if __name__ == "__main__":
    main()
