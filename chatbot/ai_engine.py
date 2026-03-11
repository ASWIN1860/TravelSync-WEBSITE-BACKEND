import os
from groq import Groq
from django.conf import settings
from dotenv import load_dotenv

load_dotenv()  # this loads the .env file

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

client = Groq(api_key=GROQ_API_KEY)

LANGUAGE_MODEL = "llama-3.1-8b-instant"

RAG_FILE_PATH = os.path.join(
    settings.BASE_DIR,
    "chatbot",
    "data",
    "rag.txt"
)

with open(RAG_FILE_PATH, "r", encoding="utf-8") as file:
    data_set = [line.strip() for line in file.readlines() if line.strip()]


def simple_search(query):
    query_words = set(query.lower().split())

    scored = []
    for chunk in data_set:
        chunk_words = set(chunk.lower().split())
        score = len(query_words.intersection(chunk_words))
        scored.append((chunk, score))

    scored.sort(key=lambda x: x[1], reverse=True)
    return " ".join([item[0] for item in scored[:3]])


def get_rag_response(user_query):
    context_text = simple_search(user_query)


    instruction_prompt = (
        f"Role: You are TravelZync AI, a specialized local bus guide.\n\n"
        f"Strict Guidelines:\n"
        f"1. If the user says 'hi', 'how are you', or similar greetings, respond naturally as a helpful AI.\n"
        f"2. If the question is about bus travel: Check the Context below. If the answer is there, provide it. "
        f"If the answer is NOT in the Context, say: 'The information is not in our data base, but we will improve our data base for further future.'\n"
        f"3. If the question is about any other topic (politics, sports, general facts, etc.), say: "
        f"'I\'m a chatbot for your local bus guidance, i can\'t give you other information.'\n"
        f"4. Do not use outside knowledge to answer bus questions; use ONLY the provided Context.\n\n"
        f"5. Use the previous question and response if required.\n\n"
        f"Context:\n{context_text}\n\n"
        f"User Question: {user_query}"
    )

    chat_completion = client.chat.completions.create(
        messages=[
            {"role": "system", "content": instruction_prompt},
            {"role": "user", "content": user_query}
        ],
        model=LANGUAGE_MODEL,
        temperature=0.2,
    )

    return chat_completion.choices[0].message.content