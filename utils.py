from openai import OpenAI
import logging

logger = logging.getLogger(__name__)


def check_openai_api_key(api_key: str) -> bool:
    try:
        client = OpenAI(api_key=api_key)
        client.models.list()  # cheap, fast auth check
        logger.info("OpenAI API key check passed.")
        return True
    except Exception as e:
        logger.error(f"OpenAI API key check failed: {e}")
        return False


def check_job_title_valid(api_key: str, job_title: str) -> bool:

    client = OpenAI(api_key=api_key)
    prompt = "Is '{job_title}' a job title? Return 1 if it is, 0 otherwise, don't return other things."
    response = client.responses.create(model="gpt-5-nano-2025-08-07", input=prompt.format(job_title=job_title))
    assert response.output_text in ("0", "1"), f"Got invalid response from OpenAI: {response.output_text}"
    result = bool(int(response.output_text))

    logger.info(f"Job title '{job_title}' validity check: {result}")
    return result
