"""
============================================================
  IBM Watsonx.ai Translation Client
  File: app/utils/watsonx_client.py
============================================================
"""

import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)

_watsonx_client = None


def get_watsonx_client():
    """Return a cached WatsonxAI client instance."""
    global _watsonx_client
    if _watsonx_client is None:
        try:
            from ibm_watsonx_ai import APIClient, Credentials
            creds = Credentials(
                url=os.getenv("IBM_WATSONX_URL", "https://us-south.ml.cloud.ibm.com"),
                api_key=os.getenv("IBM_API_KEY", ""),
            )
            _watsonx_client = APIClient(creds)
            logger.info("IBM Watsonx client initialized.")
        except Exception as e:
            logger.error(f"Failed to initialize Watsonx client: {e}")
            raise
    return _watsonx_client


def translate_text(
    source_text: str,
    system_prompt: str,
    user_prompt: str,
    model_id: Optional[str] = None,
    max_new_tokens: int = 4096,
    temperature: float = 0.2,
) -> str:
    """
    Call IBM Watsonx Granite to translate text.

    Args:
        source_text: The original text (used only for logging)
        system_prompt: System-level instructions (from agent_instructions)
        user_prompt: The full user-turn prompt with RAG context + source
        model_id: Watsonx model ID override
        max_new_tokens: Max tokens in the response
        temperature: Sampling temperature (low = deterministic)

    Returns:
        Translated text string
    """
    model_id = model_id or os.getenv("TRANSLATION_MODEL", "ibm/granite-3-3-8b-instruct")
    project_id = os.getenv("IBM_WATSONX_PROJECT_ID", "")

    try:
        from ibm_watsonx_ai.foundation_models import ModelInference
        from ibm_watsonx_ai.metanames import GenTextParamsMetaNames as Params

        client = get_watsonx_client()

        params = {
            Params.MAX_NEW_TOKENS: max_new_tokens,
            Params.TEMPERATURE: temperature,
            Params.REPETITION_PENALTY: 1.05,
            Params.STOP_SEQUENCES: [],
        }

        model = ModelInference(
            model_id=model_id,
            api_client=client,
            project_id=project_id,
            params=params,
        )

        # Build chat messages
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        logger.info(f"Calling Watsonx [{model_id}] | input ~{len(source_text)} chars")
        response = model.chat(messages=messages)

        # Extract content from response
        translated = ""
        if isinstance(response, dict):
            choices = response.get("choices", [])
            if choices:
                translated = choices[0].get("message", {}).get("content", "")
            if not translated:
                translated = response.get("results", [{}])[0].get("generated_text", "")
        elif hasattr(response, "choices"):
            translated = response.choices[0].message.content
        else:
            translated = str(response)

        logger.info(f"Translation complete: {len(translated)} chars returned.")
        return translated.strip()

    except ImportError:
        logger.error("ibm-watsonx-ai not installed. Run: pip install ibm-watsonx-ai")
        return "[Error: ibm-watsonx-ai package not installed]"
    except Exception as e:
        logger.error(f"Translation API call failed: {e}", exc_info=True)
        raise


def test_connection() -> dict:
    """Test the Watsonx connection and return status info."""
    try:
        client = get_watsonx_client()
        return {"status": "connected", "url": os.getenv("IBM_WATSONX_URL")}
    except Exception as e:
        return {"status": "error", "error": str(e)}
