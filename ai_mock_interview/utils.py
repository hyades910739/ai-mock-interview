import logging

from openai import OpenAI

logger = logging.getLogger(__name__)

CHECKED_JOB_TITLES = {
    "software engineer": 1,
    "senior software engineer": 1,
    "backend engineer": 1,
    "frontend engineer": 1,
    "full stack engineer": 1,
    "machine learning engineer": 1,
    "data engineer": 1,
    "data scientist": 1,
    "data analyst": 1,
    "data architect": 1,
    "devops engineer": 1,
    "site reliability engineer": 1,
    "cloud engineer": 1,
    "platform engineer": 1,
    "infrastructure engineer": 1,
    "mobile engineer": 1,
    "ios engineer": 1,
    "android engineer": 1,
    "qa engineer": 1,
    "test engineer": 1,
    "automation engineer": 1,
    "security engineer": 1,
    "application security engineer": 1,
    "network engineer": 1,
    "systems engineer": 1,
    "embedded systems engineer": 1,
    "firmware engineer": 1,
    "hardware engineer": 1,
    "robotics engineer": 1,
    "ai engineer": 1,
    "nlp engineer": 1,
    "computer vision engineer": 1,
    "data platform engineer": 1,
    "big data engineer": 1,
    "etl engineer": 1,
    "search engineer": 1,
    "recommendation systems engineer": 1,
    "game engineer": 1,
    "graphics engineer": 1,
    "build engineer": 1,
    "release engineer": 1,
    "reliability engineer": 1,
    "observability engineer": 1,
    "database engineer": 1,
    "distributed systems engineer": 1,
    "performance engineer": 1,
    "storage engineer": 1,
    "web engineer": 1,
    "api engineer": 1,
}


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
    job_title = job_title.strip().lower()
    if job_title in CHECKED_JOB_TITLES:
        v = CHECKED_JOB_TITLES[job_title]
        return v
    logger.info(f"Unknown job title: {job_title}, check through OpenAI API...")

    client = OpenAI(api_key=api_key)
    prompt = "Is '{job_title}' a job title? Return 1 if it is, 0 otherwise, don't return other things."
    response = client.responses.create(model="gpt-5-nano-2025-08-07", input=prompt.format(job_title=job_title))
    assert response.output_text in ("0", "1"), f"Got invalid response from OpenAI: {response.output_text}"
    result = bool(int(response.output_text))

    logger.info(f"Job title '{job_title}' validity check: {result}")
    CHECKED_JOB_TITLES[job_title] = result
    return result
