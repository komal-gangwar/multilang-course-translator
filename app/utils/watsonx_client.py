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

# ── Supported model registry ─────────────────────────────────────────────────
# Update this list if your Watsonx project gains / loses model access.
# The first entry is the default used when TRANSLATION_MODEL is not set in .env.
SUPPORTED_TRANSLATION_MODELS = [
    "meta-llama/llama-3-3-70b-instruct",   # best quality — default
    "meta-llama/llama-3-1-8b",
    "meta-llama/llama-3-3-70b-gptq",
    "meta-llama/llama-4-maverick-17b-128e-instruct-fp8",
    "ibm/granite-3-1-8b-base",             # IBM Granite (base, not instruct)
    "ibm/granite-4-h-small",
    "ibm/granite-8b-code-instruct",
    "mistralai/mistral-large-2512",
    "mistralai/mistral-medium-2505",
    "mistralai/mistral-small-3-1-24b-instruct-2503",
    "openai/gpt-oss-120b",
]

_DEFAULT_TRANSLATION_MODEL = SUPPORTED_TRANSLATION_MODELS[0]


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
    model_id = model_id or os.getenv("TRANSLATION_MODEL", _DEFAULT_TRANSLATION_MODEL)
    project_id = os.getenv("IBM_WATSONX_PROJECT_ID", "")

    if not project_id:
        raise ValueError(
            "IBM_WATSONX_PROJECT_ID is not set in .env. "
            "Copy .env.example → .env and fill in your Project ID."
        )

    # Warn early if the configured model is not in the known-supported list
    if model_id not in SUPPORTED_TRANSLATION_MODELS:
        logger.warning(
            f"TRANSLATION_MODEL='{model_id}' is not in the known-supported list. "
            f"If you get a 'Model not supported' error, set TRANSLATION_MODEL in .env "
            f"to one of: {SUPPORTED_TRANSLATION_MODELS}"
        )

    try:
        from ibm_watsonx_ai.foundation_models import ModelInference

        client = get_watsonx_client()

        # ModelInference without params — pass generation options directly to .chat()
        model = ModelInference(
            model_id=model_id,
            api_client=client,
            project_id=project_id,
        )

        # Build chat messages
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        # Generation parameters passed per-call (works across all SDK versions)
        gen_params = {
            "max_new_tokens": max_new_tokens,
            "temperature": temperature,
            "repetition_penalty": 1.05,
        }

        logger.info(
            f"Calling Watsonx [{model_id}] | "
            f"input ~{len(source_text)} chars | "
            f"max_new_tokens={max_new_tokens}"
        )
        response = model.chat(messages=messages, params=gen_params)

        # Extract content — handle both dict and object response shapes
        translated = ""
        if isinstance(response, dict):
            choices = response.get("choices", [])
            if choices:
                translated = (
                    choices[0].get("message", {}).get("content", "")
                    or choices[0].get("text", "")
                )
            if not translated:
                # Fallback for generate-style responses
                results = response.get("results", [])
                if results:
                    translated = results[0].get("generated_text", "")
        elif hasattr(response, "choices") and response.choices:
            msg = response.choices[0].message
            translated = msg.content if hasattr(msg, "content") else str(msg)
        else:
            translated = str(response)

        if not translated.strip():
            logger.warning("Watsonx returned an empty translation response.")

        logger.info(f"Translation complete: {len(translated)} chars returned.")
        return translated.strip()

    except ImportError:
        logger.error("ibm-watsonx-ai not installed. Run: pip install ibm-watsonx-ai")
        return "[Error: ibm-watsonx-ai package not installed]"
    except Exception as e:
        err = str(e)
        # Provide actionable guidance for the most common error
        if "not supported" in err and "Supported models" in err:
            logger.error(
                f"Model '{model_id}' is not available in your Watsonx project.\n"
                f"Set TRANSLATION_MODEL in your .env to one of the supported models.\n"
                f"Recommended: TRANSLATION_MODEL={_DEFAULT_TRANSLATION_MODEL}\n"
                f"Full error: {err}"
            )
        else:
            logger.error(f"Translation API call failed: {e}", exc_info=True)
        raise


def test_connection() -> dict:
    """Test the Watsonx connection and return status info."""
    try:
        client = get_watsonx_client()
        current_model = os.getenv("TRANSLATION_MODEL", _DEFAULT_TRANSLATION_MODEL)
        return {
            "status": "connected",
            "url": os.getenv("IBM_WATSONX_URL"),
            "current_model": current_model,
            "model_supported": current_model in SUPPORTED_TRANSLATION_MODELS,
            "supported_models": SUPPORTED_TRANSLATION_MODELS,
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}
