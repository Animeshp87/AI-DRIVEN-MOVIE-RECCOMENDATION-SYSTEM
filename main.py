"""
This script builds the recommendation database for the Streamlit app.

4-logon division (high level):
Person 1 (Database manager): dataset -> tags -> movies_list.pkl
Person 3 (Recommender backend): tags vectorization -> similarity matrix
Person 4 (Frontend/UI): app.py ke liye ready-to-load pickles
Person 2 (Poster/Assets): posters are generated inside app.py, not here.
"""

import os
import pickle

import pandas as pd
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.metrics.pairwise import cosine_similarity


# Memory guard:
# Full dataset (10k) par similarity matrix 10k x 10k banti hai (bahut memory).
# So we cap to a safe number for a smooth demo.
MAX_MOVIES = int(os.getenv("MAX_MOVIES", "3000"))


def main() -> None:
    movies = pd.read_csv("dataset.csv")

    # Feature selection
    movies = movies[["id", "title", "overview", "genre"]].copy()

    # Create a text field for similarity
    movies["tags"] = movies["overview"].fillna("").astype(str) + " " + movies["genre"].fillna("").astype(str)

    # Keep only what we need for recommendation model
    new_data = movies.drop(columns=["overview", "genre"])

    # Cap dataset size to avoid memory crash
    new_data = new_data.head(MAX_MOVIES).reset_index(drop=True)

    # Vectorize tags (keep as sparse; don't convert to dense)
    cv = CountVectorizer(max_features=10000, stop_words="english")
    vector = cv.fit_transform(new_data["tags"].values.astype("U"))

    # Build cosine similarity (dense output, but smaller due to MAX_MOVIES)
    similarity = cosine_similarity(vector).astype("float32")

    with open("movies_list.pkl", "wb") as f:
        pickle.dump(new_data, f)

    with open("similarity.pkl", "wb") as f:
        pickle.dump(similarity, f)

    print(f"Generated movies_list.pkl with {len(new_data)} rows")
    print(f"Generated similarity.pkl with shape {similarity.shape}")


if __name__ == "__main__":
    main()

