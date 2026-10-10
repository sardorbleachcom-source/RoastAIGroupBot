import aiohttp
from app import config

API_URL = "https://api.groq.com/openai/v1/chat/completions"

async def ask_groq(messages, max_tokens=700):
    max_tokens = max(1, int(max_tokens))
    if not config.GROQ_API_KEY:
        raise RuntimeError("GROQ_API_KEY .env faylida kiritilmagan")

    payload = {
        "model": config.GROQ_MODEL,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": 0.85,
    }
    headers = {
        "Authorization": f"Bearer {config.GROQ_API_KEY}",
        "Content-Type": "application/json",
    }
    timeout = aiohttp.ClientTimeout(total=60)

    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.post(
            API_URL, json=payload, headers=headers
        ) as response:
            data = await response.json(content_type=None)

            if response.status >= 400:
                error = data.get("error", {}).get(
                    "message", "Groq so'rovi bajarilmadi"
                )
                raise RuntimeError(f"Groq HTTP {response.status}: {error}")

            choices = data.get("choices", [])
            if not choices:
                raise RuntimeError("Groq javobi bo'sh")

            answer = choices[0].get("message", {}).get("content") or ""
            tokens = int(data.get("usage", {}).get("total_tokens", 0))
            return answer, tokens
