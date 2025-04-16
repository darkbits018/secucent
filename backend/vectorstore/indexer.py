import os
import faiss
import pickle
import numpy as np
from llm.gemini import embed_text


def save_guide_embeddings(guide_id, chunks):
    """
    Embeds the given text chunks and saves the FAISS index + chunk data to disk.
    """
    print(f"💾 Saving vectorstore for guide_id={guide_id}...")

    embeddings = [embed_text(chunk, is_query=False) for chunk in chunks]
    dim = len(embeddings[0])
    index = faiss.IndexFlatL2(dim)
    index.add(np.array(embeddings).astype("float32"))

    guide_dir = f"vectorstores/guide_{guide_id}"
    os.makedirs(guide_dir, exist_ok=True)
    faiss.write_index(index, f"{guide_dir}/index.faiss")
    with open(f"{guide_dir}/chunks.pkl", "wb") as f:
        pickle.dump(chunks, f)

    print(f"✅ Guide {guide_id} indexed and saved.\n")
