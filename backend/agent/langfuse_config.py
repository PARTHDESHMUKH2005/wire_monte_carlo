import os
import logging

logger = logging.getLogger(__name__)

LANGFUSE_PUBLIC_KEY = os.environ.get("LANGFUSE_PUBLIC_KEY", "")
LANGFUSE_SECRET_KEY = os.environ.get("LANGFUSE_SECRET_KEY", "")
LANGFUSE_HOST = os.environ.get("LANGFUSE_HOST", "https://cloud.langfuse.com")

_langfuse_handler = None
_langfuse_client = None


def init_langfuse():
    global _langfuse_client, _langfuse_handler
    if _langfuse_handler is not None:
        return
    if not LANGFUSE_PUBLIC_KEY or not LANGFUSE_SECRET_KEY:
        logger.info("Langfuse keys not set — tracing disabled")
        return
    try:
        from langfuse.callback import CallbackHandler
        _langfuse_handler = CallbackHandler(
            secret_key=LANGFUSE_SECRET_KEY,
            public_key=LANGFUSE_PUBLIC_KEY,
            host=LANGFUSE_HOST,
        )
        logger.info("Langfuse CallbackHandler initialized")
    except ImportError:
        try:
            from langfuse import Langfuse
            _langfuse_client = Langfuse(
                public_key=LANGFUSE_PUBLIC_KEY,
                secret_key=LANGFUSE_SECRET_KEY,
                host=LANGFUSE_HOST,
            )
            try:
                _langfuse_handler = _langfuse_client.get_langfuse_handler()
            except AttributeError:
                pass
            logger.info("Langfuse client initialized")
        except Exception as e:
            logger.warning(f"Langfuse init failed: {e}")
    except Exception as e:
        logger.warning(f"Langfuse CallbackHandler init failed: {e}")


def get_langfuse_handler():
    if _langfuse_handler is None:
        init_langfuse()
    return _langfuse_handler


def get_langfuse_client():
    global _langfuse_client
    if _langfuse_client is None and LANGFUSE_PUBLIC_KEY and LANGFUSE_SECRET_KEY:
        try:
            from langfuse import Langfuse
            _langfuse_client = Langfuse(
                public_key=LANGFUSE_PUBLIC_KEY,
                secret_key=LANGFUSE_SECRET_KEY,
                host=LANGFUSE_HOST,
            )
        except Exception:
            pass
    return _langfuse_client


def track_cost(run_id: str, tokens_in: int, tokens_out: int, model: str):
    client = get_langfuse_client()
    if client is None:
        return
    try:
        client.generation(
            name="vera_llm_call",
            model=model,
            usage={"input": tokens_in, "output": tokens_out},
            metadata={"run_id": run_id},
        )
    except Exception as e:
        logger.debug(f"Langfuse cost tracking failed: {e}")
