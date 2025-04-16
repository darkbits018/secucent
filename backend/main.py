from db.connection import test_db_connection
from db.fetch_guides import fetch_guides
from processing.extract import clean_guide_data
from processing.chunker import chunk_text
from vectorstore.indexer import save_guide_embeddings

def main():
    test_db_connection()
    guides = fetch_guides()

    for guide in guides:
        guide_id = guide['id']
        print(f"\n🔍 Processing guide_id={guide_id}")

        text = clean_guide_data(guide["guide_data"])
        if not text.strip():
            print(f"⚠️ Guide {guide_id} has no extractable text.")
            continue

        chunks = chunk_text(text)
        if not chunks:
            print(f"⚠️ Guide {guide_id} resulted in 0 chunks.")
            continue

        save_guide_embeddings(guide_id, chunks)


if __name__ == "__main__":
    main()
