import chromadb
from chromadb.utils import embedding_functions

def build_vector_store():
    print("Initializing ChromaDB...")
    # This creates a folder called 'rag_db' in your project
    chroma_client = chromadb.PersistentClient(path="../rag_db")
    
    # We use a fast, lightweight embedding model
    sentence_transformer_ef = embedding_functions.SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2")
    
    # Create or reset our collection
    collection = chroma_client.get_or_create_collection(
        name="ruse_website_map", 
        embedding_function=sentence_transformer_ef
    )
    
    print("Reading website data...")
    with open("ruse_sitemap.txt", "r", encoding="utf-8") as file:
        lines = file.readlines()
        
    documents = []
    ids = []
    
    for idx, line in enumerate(lines):
        text = line.strip()
        if text:  # Ignore empty lines
            documents.append(text)
            ids.append(f"fact_{idx}")
            
    print(f"Embedding {len(documents)} facts into the database...")
    collection.add(
        documents=documents,
        ids=ids
    )
    print("Success! RAG Database built.")

if __name__ == "__main__":
    build_vector_store()