from openai import OpenAI


def check_openai_api_key(api_key: str) -> bool:
    try:
        client = OpenAI(api_key=api_key)
        client.models.list()  # cheap, fast auth check
        return True
    except Exception:
        return False


def check_job_title_valid(api_key: str, job_title: str) -> bool:

    client = OpenAI(api_key=api_key)
    prompt = "Is '{job_title}' a job title? Return 1 if it is, 0 otherwise, don't return other things."
    response = client.responses.create(model="gpt-5-nano-2025-08-07", input=prompt.format(job_title=job_title))
    assert response.output_text in ("0", "1"), f"Got invalid response from OpenAI: {response.output_text}"
    result = bool(int(response.output_text))

    return result
