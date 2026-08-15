import os
import json
import logging
import hashlib
import numpy as np
from typing import List, Dict, Any, Optional
from openai import OpenAI
from backend.app.core.config import settings

logger = logging.getLogger(__name__)

# Mock settings
MOCK_MODE = os.environ.get("MOCK_LLM", "False").lower() in ("true", "1", "yes")

_mock_responses: Dict[str, Any] = {}

def set_mock_response(prompt_substring: str, response: Any):
    """Set a mock response for tests when a prompt contains the substring."""
    _mock_responses[prompt_substring] = response

def clear_mock_responses():
    _mock_responses.clear()

def get_openai_client() -> OpenAI:
    """Get configured OpenAI client."""
    return OpenAI(
        api_key=settings.OPENAI_API_KEY,
        base_url=settings.OPENAI_API_BASE
    )

def generate_chat_completion(
    messages: List[Dict[str, str]],
    temperature: float = 0.0,
    json_mode: bool = False,
    max_tokens: Optional[int] = None
) -> str:
    """
    Generate chat completion from messages.
    Supports a mock mode for tests.
    """
    # Build prompt representation for mocking check
    full_prompt = "\n".join([f"{m.get('role')}: {m.get('content')}" for m in messages])
    
    if MOCK_MODE or settings.OPENAI_API_KEY == "mock-key-for-testing":
        # Check registered mock responses (case-insensitive)
        for substring, mock_res in _mock_responses.items():
            if substring.lower() in full_prompt.lower():
                if isinstance(mock_res, str):
                    return mock_res
                return json.dumps(mock_res)
        
        # Fallback generic mock response depending on json_mode
        if json_mode:
            # Try to return a structured JSON based on context clues
            if "coordinator" in full_prompt.lower() or "decompose" in full_prompt.lower():
                return json.dumps({
                    "tasks": [
                        {"query": "mock task 1", "agent": "case_law", "reason": "test case"},
                        {"query": "mock task 2", "agent": "statute", "reason": "test statute"}
                    ]
                })
            elif "verification" in full_prompt.lower() or "verify" in full_prompt.lower():
                return json.dumps({
                    "verification_results": [
                        {
                            "claim": "Mock claim",
                            "supported": True,
                            "evidence_index": 1,
                            "confidence": 0.95,
                            "issues": []
                        }
                    ]
                })
            elif "reflection" in full_prompt.lower() or "reflect" in full_prompt.lower():
                return json.dumps({
                    "sufficient": True,
                    "reasoning": "Sufficient evidence found.",
                    "follow_up_tasks": []
                })
            elif "synthesis" in full_prompt.lower() or "synthesize" in full_prompt.lower():
                return json.dumps({
                    "answer": "This is a mock synthesized legal answer [1].",
                    "conflicts": []
                })
            return json.dumps({"message": "Mock JSON response"})
        return "This is a mock LLM response."

    try:
        client = get_openai_client()
        kwargs: Dict[str, Any] = {
            "model": settings.LLM_MODEL,
            "messages": messages,
            "temperature": temperature,
        }
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}
        if max_tokens:
            kwargs["max_tokens"] = max_tokens

        response = client.chat.completions.create(**kwargs)
        return response.choices[0].message.content or ""
    except Exception as e:
        logger.error(f"Error in LLM chat completion: {e}")
        raise e

def generate_embeddings(texts: List[str]) -> List[List[float]]:
    """
    Generate embeddings for list of texts.
    If in mock mode, returns a deterministic unit vector based on the text hash.
    """
    if MOCK_MODE or settings.OPENAI_API_KEY == "mock-key-for-testing":
        embeddings = []
        for text in texts:
            # Deterministic vector generation using md5 hash of text
            hasher = hashlib.md5(text.encode("utf-8"))
            seed = int(hasher.hexdigest()[:8], 16)
            rng = np.random.default_rng(seed)
            vec = rng.standard_normal(1536).tolist()
            # Normalize vector to unit length
            norm = sum(x*x for x in vec) ** 0.5
            norm_vec = [x / norm for x in vec] if norm > 0 else vec
            embeddings.append(norm_vec)
        return embeddings

    try:
        client = get_openai_client()
        response = client.embeddings.create(
            input=texts,
            model=settings.EMBEDDING_MODEL
        )
        return [data.embedding for data in response.data]
    except Exception as e:
        logger.error(f"Error in generating embeddings: {e}")
        raise e
