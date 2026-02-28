import ollama
import os
from django.conf import settings
from functools import lru_cache

EMBEDDING_MODEL = "hf.co/CompendiumLabs/bge-base-en-v1.5-gguf"
LANGUAGE_MODEL = "hf.co/bartowski/Llama-3.2-1B-Instruct-GGUF"

RAG_FILE_PATH = os.path.join(
    settings.BASE_DIR,
    "chatbot",
    "data",
    "rag.txt"
)

# ==============================
# Load dataset once
# ==============================
with open(RAG_FILE_PATH, "r", encoding="utf-8") as file:
    DATA_SET = [line.strip() for line in file.readlines() if line.strip()]


# ==============================
# Build vector DB once
# ==============================
@lru_cache(maxsize=1)
def build_vector_db():
    vector_db = []
    for chunk in DATA_SET:
        embedding = ollama.embed(
            model=EMBEDDING_MODEL,
            input=chunk
        )['embeddings'][0]
        vector_db.append((chunk, embedding))
    return vector_db


# ==============================
# Cosine similarity
# ==============================
def cosine_similarity(a, b):
    dot_product = sum(x * y for x, y in zip(a, b))
    norm_a = sum(x**2 for x in a) ** 0.5
    norm_b = sum(x**2 for x in b) ** 0.5
    return dot_product / (norm_a * norm_b) if (norm_a * norm_b) != 0 else 0


# ==============================
# Main RAG function
# ==============================
def get_rag_response(user_query):

    vector_db = build_vector_db()

    # Embed query
    query_embedding = ollama.embed(
        model=EMBEDDING_MODEL,
        input=user_query
    )['embeddings'][0]

    # Rank
    similarities = sorted(
        [(chunk, cosine_similarity(query_embedding, emb)) for chunk, emb in vector_db],
        key=lambda x: x[1],
        reverse=True
    )

    context_text = " ".join([item[0] for item in similarities[:3]])

    # instruction_prompt = (
    #     "You are TravelSync AI assistant. "
    #     "Answer strictly based on the provided context .some bus guide "
    #     " Use only the following pieces of context to answer  the question about bus travel only"
    #     "If answer not in context, say you don't know.\n\n"
    #     f"Context:\n{context_text}"
    # )

    instruction_prompt = (
    "You are TravelSync AI Assistant.\n"
    "Answer strictly based only on the provided context about bus travel.\n"
    "Do not create new information.\n"
    "If the answer is not present in the context, respond with:\n"
    "'The requested information is currently not available in the provided context.'\n\n"
    f"Context:\n{context_text}"
)

    response = ollama.chat(
        model=LANGUAGE_MODEL,
        messages=[
            {'role': 'system', 'content': instruction_prompt},
            {'role': 'user', 'content': user_query}
        ]
    )

    return response['message']['content']