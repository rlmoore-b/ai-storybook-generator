import os
from openai import OpenAI, AsyncOpenAI

# Synchronous client (for existing agents)
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Asynchronous client (for parallel image/prompt generation)
aclient = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def call_model(prompt: str, max_tokens=3000, temperature=0.1) -> str:
    """Synchronous call for sequential agents (Planner, Writer, etc.)"""
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=max_tokens,
        temperature=temperature,
    )
    return response.choices[0].message.content

async def acall_model(prompt: str, max_tokens=3000, temperature=0.1) -> str:
    """Async call for parallel tasks (Image Prompts)"""
    response = await aclient.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=max_tokens,
        temperature=temperature,
    )
    return response.choices[0].message.content