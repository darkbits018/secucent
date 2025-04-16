import os
import pickle
import faiss
import numpy as np
from llm.gemini import embed_text, generate_answer


def answer_question(guide_id, query, top_k=5, relevance_threshold=0.65):
    """
    Loads a guide's vectorstore, embeds the query, searches for relevant chunks,
    and generates an answer using Gemini with or without context.
    """
    # Load vectorstore and chunks
    index_path = f"vectorstores/guide_{guide_id}/index.faiss"
    chunks_path = f"vectorstores/guide_{guide_id}/chunks.pkl"

    if not os.path.exists(index_path) or not os.path.exists(chunks_path):
        return "❌ Vectorstore not found for the specified guide."

    index = faiss.read_index(index_path)
    with open(chunks_path, "rb") as f:
        chunks = pickle.load(f)

    # Embed query
    query_embedding = embed_text(query, is_query=True)

    # Search FAISS index
    D, I = index.search(np.array([query_embedding]).astype("float32"), top_k)
    retrieved_chunks = [chunks[i] for i in I[0]]
    distances = D[0]

    similarities = 1 / (1 + distances)
    print(f"🔍 Top similarity score: {similarities[0]:.4f}")

    # Use relevant chunks if score is good enough
    if similarities[0] > relevance_threshold:
        context = "\n---\n".join(dict.fromkeys(retrieved_chunks))
        prompt = f"Use the following lab guide to answer the question **clearly and concisely**:\n\n{context}\n\nQuestion: {query}\nAnswer:"
        answer = generate_answer(prompt)
        sources = "\n".join(retrieved_chunks[:2])
        return f"{answer}\n\n**Source:** Lab Guide\n\n**Details:**\n{sources}"
    else:
        print("⚠️ No strong match, falling back to Gemini + weak context.")
        context = "\n---\n".join(dict.fromkeys(retrieved_chunks))
        prompt = f"The lab guide did not contain a strong match, but here's what it had:\n\n{context}\n\nQuestion: {query}\nAnswer clearly and concisely:"
        answer = generate_answer(prompt)
        return f"{answer}\n\n**Source:** Gemini + Top Guide Chunks\n\n**Chunks Used:**\n{context}"
