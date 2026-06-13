import os
import logging

logger = logging.getLogger(__name__)

try:
    import litellm
    _LITELLM_AVAILABLE = True
except ImportError:
    _LITELLM_AVAILABLE = False
    logger.warning("litellm not installed — LLM calls disabled")

_AVAILABLE_KEYS = [k for k in (
    "OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GROQ_API_KEY",
    "AZURE_API_KEY", "GEMINI_API_KEY", "TOGETHERAI_API_KEY",
    "LITELLM_API_KEY",
) if os.environ.get(k)]


def _default_models():
    if "GROQ_API_KEY" in _AVAILABLE_KEYS:
        return ("groq/llama-3.3-70b-versatile", "groq/llama-3.1-8b-instant", "groq/llama-3.2-3b-preview")
    if "OPENAI_API_KEY" in _AVAILABLE_KEYS:
        return ("gpt-4o", "gpt-4o-mini", "gpt-3.5-turbo")
    if "ANTHROPIC_API_KEY" in _AVAILABLE_KEYS:
        return ("claude-3-5-sonnet-20241022", "claude-3-haiku-20240307", "claude-3-opus-20240229")
    if "GEMINI_API_KEY" in _AVAILABLE_KEYS:
        return ("gemini/gemini-1.5-pro", "gemini/gemini-1.5-flash", "gemini/gemini-1.5-flash-8b")
    return ("gpt-4o", "claude-3-5-sonnet-20241022", "gemini/gemini-1.5-flash")


PRIMARY_MODEL = os.environ.get("LITELLM_PRIMARY_MODEL", _default_models()[0])
SECONDARY_MODEL = os.environ.get("LITELLM_SECONDARY_MODEL", _default_models()[1])
TERTIARY_MODEL = os.environ.get("LITELLM_TERTIARY_MODEL", _default_models()[2])

MAX_COST_PER_REQUEST = 0.10

_NO_LLM_KEYS = not bool(_AVAILABLE_KEYS)


def _is_auth_error(e: Exception) -> bool:
    err_str = str(e).lower()
    return (
        "authenticationerror" in type(e).__name__.lower()
        or "auth_error" in type(e).__name__.lower()
        or "api_key" in err_str
        or "api key" in err_str
        or "unauthorized" in err_str
        or "401" in err_str
        or "403" in err_str
    )


def get_llm_response(messages: list, model: str = None, temperature: float = 0.3, max_tokens: int = 2048, response_format=None):
    if not _LITELLM_AVAILABLE:
        raise RuntimeError("litellm package not installed")
    if _NO_LLM_KEYS:
        raise RuntimeError("No LLM API keys configured")
    model = model or PRIMARY_MODEL

    def _do_call(m):
        kwargs = dict(
            model=m,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        if response_format:
            kwargs["response_format"] = response_format
        return litellm.completion(**kwargs)

    try:
        return _do_call(model)
    except Exception as e:
        if _is_auth_error(e):
            logger.debug(f"LLM key invalid for {model}")
            raise RuntimeError(f"No valid API key for {model}")

        logger.debug(f"Primary model {model} failed: {e}")
        fallback_models = []
        if model == PRIMARY_MODEL:
            fallback_models = [SECONDARY_MODEL, TERTIARY_MODEL]
        elif model == SECONDARY_MODEL:
            fallback_models = [TERTIARY_MODEL]
        else:
            raise

        for fb in fallback_models:
            try:
                response = _do_call(fb)
                logger.debug(f"Fell back to {fb} successfully")
                return response
            except Exception as fb_e:
                if _is_auth_error(fb_e):
                    raise RuntimeError(f"No valid API key for any model")
                logger.debug(f"Fallback {fb} also failed: {fb_e}")
                continue
        raise


def get_model_for_intent(intent: str) -> str:
    if intent in ("report", "morning_brief", "forecast"):
        return PRIMARY_MODEL
    if intent in ("scenario", "rebalance"):
        return SECONDARY_MODEL
    return TERTIARY_MODEL
