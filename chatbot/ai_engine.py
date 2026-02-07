import ollama
import os
from django.conf import settings
# with open("rag.txt", "r") as file:
#         # filter out empty lines to ensure the vector DB only contains useful info
#     data_set = [line.strip() for line in file.readlines() if line.strip()]



RAG_FILE_PATH = os.path.join(
    settings.BASE_DIR,
    "chatbot",
    "data",
    "rag.txt"
)

with open(RAG_FILE_PATH, "r", encoding="utf-8") as file:
    data_set = [line.strip() for line in file.readlines() if line.strip()]


def get_rag_response(user_query):
    
    EMBEDDING_MODEL = "hf.co/CompendiumLabs/bge-base-en-v1.5-gguf"
    LANGUAGE_MODEL = "hf.co/bartowski/Llama-3.2-1B-Instruct-GGUF"
    
    
    # Create Vector Database (Embeddings)
    vector_db = []
    for chunk in data_set:
        embedding = ollama.embed(model=EMBEDDING_MODEL, input=chunk)['embeddings'][0]
        vector_db.append((chunk, embedding))

    # Retrieval Logic (Cosine Similarity)
    def cosine_similarity(a, b):
        dot_product = sum(x * y for x, y in zip(a, b))
        norm_a = sum(x**2 for x in a) ** 0.5
        norm_b = sum(x**2 for x in b) ** 0.5
        return dot_product / (norm_a * norm_b) if (norm_a * norm_b) != 0 else 0

    # Get query embedding
    query_embedding = ollama.embed(model=EMBEDDING_MODEL, input=user_query)['embeddings'][0]
    
    # Rank chunks by similarity
    similarities = sorted(
        [(chunk, cosine_similarity(query_embedding, emb)) for chunk, emb in vector_db],
        key=lambda x: x[1], 
        reverse=True
    )
    
    # Take top 3 relevant context pieces
    context_text = " ".join([item[0] for item in similarities[:3]])

    # 5. Generate Response
    instruction_prompt = (
        f"You are a helpful chatbot. Use only the following pieces of context to answer "
        f"the question. Do not create new information: {context_text}"
    )

    response = ollama.chat(
        model=LANGUAGE_MODEL,
        messages=[
            {'role': 'system', 'content': instruction_prompt},
            {'role': 'user', 'content': user_query}
        ]
    )
    
    return response['message']['content']
