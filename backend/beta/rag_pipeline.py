import os
import json
import faiss # Vector index library for fast similarity search
import pickle
import numpy as np
import mysql.connector
import google.generativeai as genai
from dotenv import load_dotenv # For loading env vars from .env
from bs4 import BeautifulSoup # To strip HTML tags
from langchain.text_splitter import RecursiveCharacterTextSplitter # Smart text chunking
from llm.gemini import embed_text, generate_answer

# -------------------- Setup --------------------
load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY")) # Auth Gemini API


# -------------------- DB Config --------------------
def get_db_connection():
    return mysql.connector.connect(
        host=os.getenv("DB_HOST"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME")
    )


def test_db_connection():
    # Quick sanity check for DB connection
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT DATABASE();")
        db_name = cursor.fetchone()[0]
        print(f"✅ Connected to database: {db_name}")
        cursor.close()
        conn.close()
    except Exception as e:
        print("❌ DB connection failed:", e)


# -------------------- Fetch Guides --------------------
def fetch_guides():
    # Pull all guides from DB (assumes there's a `guide_data` column with JSON)
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT id, guide_data FROM guides")
    guides = cursor.fetchall()
    cursor.close()
    conn.close()
    return guides


# -------------------- Debug Helper --------------------
def debug_guide_structure(guide_id):
    # Debug helper to peek at raw guide JSON from DB
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT guide_data FROM guides WHERE id = %s", (guide_id,))
    row = cursor.fetchone()
    cursor.close()
    conn.close()

    if row:
        print(f"\n📦 Raw guide_data for ID {guide_id}:\n")
        try:
            guide_json = json.loads(row['guide_data'])
            print(json.dumps(guide_json, indent=2)[:2000])  # Only first 2k chars to avoid terminal meltdown
        except Exception as e:
            print("❌ Failed to parse guide_data:", e)
    else:
        print("❌ Guide not found.")


# -------------------- Extract Text --------------------
def clean_guide_data(guide_data):
    # Converts the guide's JSON into clean, plain text using BeautifulSoup
    try:
        parsed = json.loads(guide_data)
        if not isinstance(parsed, dict):
            return ""
        all_html = ""
        for _, section in parsed.items():
            if isinstance(section, dict):
                inner_sections = section.get("sections", {})
                for _, subsection in inner_sections.items():
                    html = subsection.get("content", {}).get("value", "")
                    all_html += html + "\n"
        soup = BeautifulSoup(all_html, "html.parser")
        return soup.get_text(separator="\n") # Keep structure, avoid soup vomitting
    except Exception as e:
        print("❌ Failed to extract guide text:", e)
        return ""


# -------------------- Chunk Text --------------------
def chunk_text(text):
    # Split long text into overlapping chunks for embedding (RAG-style)
    splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=100)
    return splitter.split_text(text)


# -------------------- Embedding --------------------

# get_embedding is imported from embedding_provider.py
# This is your content embedding function, used both for queries and documents

# def get_embedding(text):
#     response = genai.embed_content(
#         model="models/embedding-001",
#         content=text,
#         task_type="retrieval_document"
#     )
#     return response["embedding"]


def get_query_embedding(query):
    response = genai.embed_content(
        model="models/embedding-001",
        content=query,
        task_type="retrieval_query"
    )
    return response["embedding"]


# -------------------- Save Guide Embeddings --------------------
def save_guide_embeddings(guide_id, chunks):
    # Create and persist FAISS vector index + raw chunks for a guide

    print(f"💾 Saving vectorstore for guide_id={guide_id}...")
    embeddings = [embed_text(chunk, is_query=False) for chunk in chunks]
    dim = len(embeddings[0])
    index = faiss.IndexFlatL2(dim) # Fast, flat L2 index (no fancy tree structure)
    index.add(np.array(embeddings).astype("float32"))

    # Save the index + raw chunks to disk
    os.makedirs(f"vectorstores/guide_{guide_id}", exist_ok=True)
    faiss.write_index(index, f"vectorstores/guide_{guide_id}/index.faiss")
    with open(f"vectorstores/guide_{guide_id}/chunks.pkl", "wb") as f:
        pickle.dump(chunks, f)
    print(f"✅ Guide {guide_id} indexed and saved.\n")


# -------------------- Answer Question --------------------
def answer_question(guide_id, query, top_k=5, relevance_threshold=0.65):
    # Main RAG logic:
    # 1. Load vectorstore
    # 2. Embed query
    # 3. Search for top_k matches
    # 4. Use Gemini to generate answer based on context

    index = faiss.read_index(f"vectorstores/guide_{guide_id}/index.faiss")
    with open(f"vectorstores/guide_{guide_id}/chunks.pkl", "rb") as f:
        chunks = pickle.load(f)

    # Embed the query
    query_embedding = embed_text(query, is_query=True)

    # Search FAISS index
    D, I = index.search(np.array([query_embedding]).astype("float32"), top_k)
    retrieved_chunks = [chunks[i] for i in I[0]]
    distances = D[0]

    # Normalize similarity: convert L2 distance to confidence (optional trick) [Convert L2 distance into a "confidence"-ish similarity score]
    similarities = 1 / (1 + distances)
    print(f"🔍 Top similarity score: {similarities[0]:.4f}")

    # If top match is good enough, go full RAG
    if similarities[0] > relevance_threshold:
        unique_chunks = list(dict.fromkeys(retrieved_chunks))
        context = "\n---\n".join(unique_chunks)
        prompt = f"Use the following lab guide to answer the question **clearly and concisely**:\n\n{context}\n\nQuestion: {query}\nAnswer:"
        model = genai.GenerativeModel("gemini-2.0-flash")
        answer = generate_answer(prompt)
        sources = "\n".join(unique_chunks[:2])  # cleaner
        return f"{answer}\n\n**Source:** Lab Guide\n\n**Details:**\n{sources}"
    else:
        # If confidence is low (meh), still try to answer using top chunks
        print("⚠️ No strong match, using Gemini + top guide chunks for fallback.")
        unique_chunks = list(dict.fromkeys(retrieved_chunks))
        context = "\n---\n".join(unique_chunks)
        prompt = f"The lab guide did not contain a strong match, but here's what it had:\n\n{context}\n\nQuestion: {query}\nAnswer clearly and concisely:"
        model = genai.GenerativeModel("gemini-2.0-flash")
        answer = generate_answer(prompt)
        return f"{answer.text.strip()}\n\n**Source:** Gemini + Top Guide Chunks\n\n**Chunks Used:**\n{context}"


# -------------------- Main Flow --------------------
if __name__ == "__main__":
    test_db_connection()
    guides = fetch_guides()

    for guide in guides:
        print(f"\n🔍 Processing guide_id={guide['id']}")
        text = clean_guide_data(guide["guide_data"])

        if not text.strip():
            print(f"⚠️ Guide {guide['id']} has no extractable text.")
            continue

        chunks = chunk_text(text)
        if not chunks:
            print(f"⚠️ Guide {guide['id']} resulted in 0 chunks.")
            continue

        save_guide_embeddings(guide['id'], chunks)
