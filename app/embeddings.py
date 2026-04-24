from openai import OpenAI
from langsmith.wrappers import wrap_openai

client = wrap_openai(OpenAI())

# Creates vector embedding to be stored/queried from Examples table
def embed(text: str) -> list[float]:
    response = client.embeddings.create(
        model="text-embedding-3-small",
        input=text
    )
    return response.data[0].embedding
