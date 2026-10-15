#embed_tetxs......is imported, not rewrittten 
#the embedding provider has not changed...only where the vectors get stored 

import chromadb  # Load Chroma so document text, metadata and vectors can be stored and searched.
from documents import DOCUMENTS  # Import the sample document list used to build the search index.
from knowledge import embed_text  #Imports your function that turns document text into embeddings/vectors.



chroma = chromadb.PersistentClient(path="./chroma_store")  #Creates a Chroma database and saves it permanently in a folder called chroma_store. Persistent is important: unlike your old INDEX = [], the vectors won't disappear when Python stops.

collection = chroma.get_or_create_collection(  # Open the existing collection, or create it if it does not exist.
    name="firm_documents",  # Give the collection the name used to find your stored documents.
    configuration={"hnsw": {"space": "cosine"}},  # Configure the vector index to compare embeddings using cosine distance.
)  # Finish the call and assign the returned collection to the collection variable.

def count() -> int:
    return collection.count()

def build_index() -> int:  # Define the function intended to embed documents and store them in Chroma.
    """Embed every document andn hand the vetcors to Chroma """
    texts = [doc["body"] for doc in DOCUMENTS]  # Extract the body text from each document for embedding.
    vectors, tokens = embed_text(texts, input_type="document")  # Embed the document texts and retain the vectors and token count.

    collection.upsert(  # Insert documents, or update existing records with the same IDs.
        ids=[doc["id"] for doc in DOCUMENTS],  # Use each document's unique ID as its database key.
        embeddings=vectors,  # Store the embedding vector for each document.
        documents=texts,  # Store the original text alongside its vector.
        metadatas=[  # Supply one metadata dictionary per document, in the same order.
            {"title": doc["title"], "type": doc["type"]}  # Keep the document title and category with its record.
            for doc in DOCUMENTS  # Build metadata for every document in the corpus.
        ],  # Finish the metadata list.
    )  # Save the supplied document records in the Chroma collection.
    return tokens  # Report the total embedding token usage to the caller.


def search(question:str,top_k:int = 3) -> list[dict]:  # Accept a question and a requested result limit, defaulting to three.
    """Embed the question and let Chroma do the storing."""
    if count() == 0:
        raise RuntimeError("Index is empty - call build_index() first")
    if top_k < 1:
        raise ValueError("top_k must be at least 1")
    # Wrap the question in a list because the embedding helper accepts a batch of texts.
    # Query mode tells the embedding provider this text will be used to search documents.
    query_vectors, _ = embed_text([question], input_type="query")  # Keep the batch of vectors and discard the token count using _.
    # query_vectors[0] is the vector for this one question.
    # The Chroma query and result conversion still need to be added below.
    
    result = collection.query(query_embeddings=query_vectors, n_results=top_k)  # Find the nearest documents to the question vector.
    return [  # Convert Chroma's grouped results into a list of document dictionaries.
        {
            "id": doc_id,
            "title": metadata["title"],
            "text": text,
            #!chroma will give us back distance ..lower is closer
            #we will do 1- distance in order to flip from the rerun distance, to similairty
            "score": 1 - distance,
        }
        for doc_id, text, metadata, distance in zip(  # Pair the matching fields for each retrieved document.
            result["ids"][0],  # Read document IDs for the first and only query.
            result["documents"][0],  # Read the corresponding stored document texts.
            result["metadatas"][0],  # Read each document's metadata, including its title.
            result["distances"][0],  # Read cosine distances in the same document order.
        )  # zip produces one group of matching fields per document.
    ]  # Return the completed list of search results.

# embed_texts is imported not rewritten... embedding provider hasn't changed... only the storage has
# configuration=.... -> not optional, we are choosing something different from Chromas default
# Chroma retuirn distance, we return similarity
    # in Chroma, lower is better
    # higher was better for ours.... (1 - distance) converts
# upsert instead of add -> add fails on an id that already exists, upsert overwrites
