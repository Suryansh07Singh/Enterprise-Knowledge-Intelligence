import os
from typing import AsyncGenerator, Dict, Any, List
from app.core.config import settings
from app.core.logging import logger

class LLMProvider:
    async def generate(self, prompt: str, system_instruction: str = "") -> str:
        raise NotImplementedError

    async def generate_stream(self, prompt: str, system_instruction: str = "") -> AsyncGenerator[str, None]:
        raise NotImplementedError

class GeminiLLMProvider(LLMProvider):
    def __init__(self, api_key: str):
        self.api_key = api_key

    async def generate(self, prompt: str, system_instruction: str = "") -> str:
        try:
            from google import genai
            client = genai.Client(api_key=self.api_key)
            full_prompt = f"{system_instruction}\n\n{prompt}" if system_instruction else prompt
            response = client.models.generate_content(
                model=settings.GEMINI_MODEL,
                contents=full_prompt
            )
            return response.text.strip() if response.text else ""
        except Exception as e:
            logger.error(f"Gemini API generation failed ({e}). Falling back to mock generator.")
            mock = MockLLMProvider()
            return await mock.generate(prompt, system_instruction)

    async def generate_stream(self, prompt: str, system_instruction: str = "") -> AsyncGenerator[str, None]:
        try:
            from google import genai
            client = genai.Client(api_key=self.api_key)
            full_prompt = f"{system_instruction}\n\n{prompt}" if system_instruction else prompt
            response = client.models.generate_content_stream(
                model=settings.GEMINI_MODEL,
                contents=full_prompt
            )
            for chunk in response:
                if chunk.text:
                    yield chunk.text
        except Exception as e:
            logger.error(f"Gemini streaming failed ({e}). Falling back to mock stream.")
            mock = MockLLMProvider()
            async for chunk in mock.generate_stream(prompt, system_instruction):
                yield chunk

class OpenAILLMProvider(LLMProvider):
    def __init__(self, api_key: str):
        self.api_key = api_key

    async def generate(self, prompt: str, system_instruction: str = "") -> str:
        try:
            import httpx
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    json={
                        "model": settings.OPENAI_MODEL,
                        "messages": [
                            {"role": "system", "content": system_instruction},
                            {"role": "user", "content": prompt}
                        ],
                        "temperature": 0.1
                    }
                )
                data = resp.json()
                return data["choices"][0]["message"]["content"].strip()
        except Exception as e:
            logger.error(f"OpenAI API failed ({e}). Falling back to mock generator.")
            mock = MockLLMProvider()
            return await mock.generate(prompt, system_instruction)

    async def generate_stream(self, prompt: str, system_instruction: str = "") -> AsyncGenerator[str, None]:
        # Simple non-stream fallback chunker if stream API is complex
        res = await self.generate(prompt, system_instruction)
        words = res.split(" ")
        for i in range(0, len(words), 3):
            yield " ".join(words[i:i+3]) + " "

class MockLLMProvider(LLMProvider):
    """Deterministic Mock LLM for offline testing and fallback when API keys are absent."""
    async def generate(self, prompt: str, system_instruction: str = "") -> str:
        # Extract evidence context if present
        if "CONTEXT EVIDENCE:" in prompt or "<evidence>" in prompt:
            return "Based strictly on the provided enterprise documentation, the relevant policy details confirm the requested requirements."
        return "I have reviewed the available information."

    async def generate_stream(self, prompt: str, system_instruction: str = "") -> AsyncGenerator[str, None]:
        text = await self.generate(prompt, system_instruction)
        for word in text.split(" "):
            yield word + " "

class LLMFactory:
    @staticmethod
    def get_provider() -> LLMProvider:
        provider_name = settings.PRIMARY_LLM_PROVIDER.lower()
        if provider_name == "gemini" and settings.GEMINI_API_KEY:
            return GeminiLLMProvider(settings.GEMINI_API_KEY)
        elif provider_name == "openai" and settings.OPENAI_API_KEY:
            return OpenAILLMProvider(settings.OPENAI_API_KEY)
        else:
            if settings.GEMINI_API_KEY:
                return GeminiLLMProvider(settings.GEMINI_API_KEY)
            elif settings.OPENAI_API_KEY:
                return OpenAILLMProvider(settings.OPENAI_API_KEY)
            return MockLLMProvider()

llm_factory = LLMFactory()
