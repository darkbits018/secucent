# Lab Guide AI Agent

**Overview** : This is an intelligent AI agent designed to help students understand and navigate cybersecurity lab exercises. It uses **Retrieval-Augmented Generation (RAG)** to answer student queries accurately based on lab guides stored in a MariaDB database.

**How it works** :
* Lab guides are stored in a MariaDB database as JSON. 
* The processing/extract.py file extracts and cleans the guide data, converting HTML content into plain text.
* The cleaned text is split into smaller, overlapping chunks using LangChain's RecursiveCharacterTextSplitter (in processing/chunker.py)
* Each chunk is converted into a vector embedding using an embedding model (e.g., Gemini).
* The embeddings are stored in a FAISS index for fast similarity-based searches.
* When a user asks a question, the system embeds the query and searches the FAISS index for relevant chunks.
* The top-matching chunks are used to construct a prompt for the language model, which generates a context-aware answer.

## Database Interaction

### `db/connection.py`
- Handles the connection to the MariaDB database.
- Includes a `test_db_connection` function to verify connectivity.

### `db/fetch_guides.py`
- Fetches lab guide data from the database.
- Returns a list of guides with their IDs and JSON content.

---

## Data Processing

### `processing/extract.py`
- Extracts and cleans guide data from JSON.
- Converts HTML content into plain text using BeautifulSoup.

### `processing/chunker.py`
- Splits the cleaned text into smaller chunks for embedding.
- Uses LangChain's `RecursiveCharacterTextSplitter`.

---

## Vector Store

### `vectorstore/indexer.py`
- Saves the vector embeddings for each guide into a FAISS index.
- Organizes embeddings by guide ID for efficient retrieval.

---

## Main Script

### `main.py`
- Orchestrates the entire pipeline:
  - Tests the database connection.
  - Fetches guides from the database.
  - Cleans and chunks the guide data.
  - Generates and saves embeddings for each guide.

---


## Web Interface (For Testing Only)

### `beta/rag_ui.py`
- Provides a Streamlit-based user interface for **testing purposes only**.
- Allows users to select a guide, ask questions, and view answers to verify functionality.
---



### Instructions to Run `rag_ui.py`

1. **Install Dependencies**:  
   Ensure you have Python installed and all required dependencies. Install them using:
   ```bash
   pip install -r requirements.txt
   ```

2. **Set Up the Database**:
   - Ensure the MariaDB database is running and contains the `guides` table with the required data.
   - Verify that the database connection details (e.g., host, username, password) are correctly configured in the `.env` file.

3. **Prepare the Environment**:
   - Ensure the `.env` file exists in the project root and contains the necessary environment variables, such as:
     ```
     GEMINI_API_KEY=your_gemini_api_key
     DB_HOST=your_database_host
     DB_USER=your_database_user
     DB_PASSWORD=your_database_password
     DB_NAME=your_database_name
     ```

4. **Run the Application**:  
   Navigate to the directory containing `rag_ui.py` and execute the following command:
   ```bash
   streamlit run beta/rag_ui.py
   ```

5. **Access the Web Interface**:
   - Open the URL displayed in the terminal (e.g., `http://localhost:8501`) in your web browser.
   - Use the dropdown to select a guide, type a question, and click "Ask" to get an answer.

By following these steps, you can successfully run and interact with the `rag_ui.py` application.















[//]: # ()
[//]: # (## ✅ What's Done)

[//]: # ()
[//]: # (### 🔧 Setup)

[//]: # (- Connected the app to a MySQL database where all the lab guides are stored.)

[//]: # (- Configured Gemini API using an environment variable from a `.env` file.)

[//]: # (- Kept sensitive info like API keys and DB credentials hidden using `dotenv`.)

[//]: # ()
[//]: # (### 📄 Guide Data Extraction)

[//]: # (- Pulled raw lab guide data from the database.)

[//]: # (- Parsed and cleaned the HTML inside the guide JSON to extract readable text content.)

[//]: # ()
[//]: # (### ✂️ Text Chunking)

[//]: # (- Split the cleaned text into smaller chunks to make searching more accurate.)

[//]: # (- Used LangChain's `RecursiveCharacterTextSplitter` for smart, overlap-based chunking.)

[//]: # ()
[//]: # (### 🧠 Embedding + Vector Store)

[//]: # (- Generated vector embeddings for all chunks using Gemini’s embedding model.)

[//]: # (- Stored those embeddings in a FAISS index, organized per guide ID.)

[//]: # (- Indexed data is saved locally and can be reused when answering questions.)

[//]: # ()
[//]: # (### 🔍 Question Answering Logic)

[//]: # (- Embedded user queries and searched the FAISS index to find the most relevant chunks.)

[//]: # (- Used similarity scoring to decide whether to answer using guide content or fall back to Gemini.)

[//]: # (- Constructed prompts with top-matching chunks to let Gemini generate context-aware answers.)

[//]: # (- If guide content is too weak, defaulted to a plain Gemini response with a warning.)

[//]: # ()
[//]: # (### 🖥️ Streamlit Web Interface)

[//]: # (- Created a simple UI to:)

[//]: # (  - Select a lab guide)

[//]: # (  - Enter a question)

[//]: # (  - Get an AI-generated answer)

[//]: # (  - Expand/collapse detailed source chunks used in the answer)

[//]: # ()
[//]: # ()
[//]: # (---)

[//]: # ()
[//]: # (## 🛠️ What's Next)

[//]: # ()
[//]: # (### 🔄 LLM Flexibility)

[//]: # (- Refactor Gemini integration to make it modular.)

[//]: # (- Add support for OpenAI &#40;easy switch via config&#41;.)

[//]: # ()
[//]: # (### 📡 Lab Guide Management)

[//]: # (- Auto-embed new lab guides when added to the database.)

[//]: # (- Build an admin interface to:)

[//]: # (  - debug or config guides and their embeddings)

[//]: # ()
[//]: # (### 🎙️ Voice Features)

[//]: # (- Add speech-to-text for voice input.)

[//]: # (- Add text-to-speech for voice-based agent replies.)

[//]: # ()
[//]: # (### 📈 Analytics)

[//]: # (- Log user questions and generated answers.)

[//]: # (- Store timestamps, guide IDs, and match confidence for analysis.)

[//]: # ()
[//]: # (### 🔐 Response Control)

[//]: # (- Restrict AI responses to cybersecurity and networking topics only.)

[//]: # ()
[//]: # (### 🧩 Frontend Integration &#40;React Agent&#41;)

[//]: # (- Convert backend to Flask for better integration with a React app.)

[//]: # (- Connect the agent window &#40;chat widget&#41; inside a React-based UI.)

[//]: # (- Display the agent on the lab page where it's needed.)

[//]: # (- Automatically detect which lab the agent was launched from.)

[//]: # ()
[//]: # (### ⚙️ Course & Lab Portal Integration)

[//]: # (- Add a checkbox in the course/lab creation form:)

[//]: # (  - "Enable Assistant for This Lab")

[//]: # (- Store flag in DB and use it to control agent visibility.)
