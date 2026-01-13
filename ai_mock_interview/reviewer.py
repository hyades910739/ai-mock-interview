import json
import logging
import os
import time
from typing import Union

import dotenv
from langchain_core.messages.ai import AIMessage
from langchain_core.messages.human import HumanMessage
from langchain_openai import ChatOpenAI
from pydantic import BaseModel

logger = logging.getLogger(__name__)

dotenv.load_dotenv(override=False)
MODEL_NAME = "gpt-5-nano-2025-08-07"


REVIEWER_SYSTEM_PROMPT = """
You are a hiring manager who has just finished interviewing a candidate.

You will be given:
- the applicant’s profile
- the full transcript of the interview

Your task is to evaluate the candidate and decide whether they should be hired based only on this information.

Produce a JSON object with the following fields:

1. "score"
   A letter grade from A+ to F that reflects the overall interview performance.

2. "the_chances_of_getting_this_job"
   A number from 0 to 100 representing the estimated chance (in percent) that this candidate would get the job.

3. "comments"
   Feedback to the candidate about their performance in this interview (maximum 500 words).

4. "what_to_improve"
   Specific areas the candidate should improve, based on the interview transcript (maximum 500 words).

Return ONLY valid JSON. Do not include any extra text.

Example:
{
  "score": "A-",
  "the_chances_of_getting_this_job": 85,
  "comments": "SKIPPED.",
  "what_to_improve": "SKIPPED."
}
"""


QUERY_PROMPT = """
# Applicant profile:
{applicant_profile}
# Interview transcript:
{interview_transcript}
"""

APPLICANT_PROMPT = """
# Applicant's Profile:
* Position: {position}
* Years of experience {yoe}
* CV: 
```
{cv}
```
"""


class ReviewResult(BaseModel):
    score: str
    the_chances_of_getting_this_job: float
    comments: str
    what_to_improve: str


def review(
    api_key: str,
    histories: list[Union[HumanMessage, AIMessage]],
    # interview_type: str,
    position: str,
    years_of_experience: float,
    cv: str,
) -> ReviewResult:
    """
    Diagnosis the interview result based on the history of the whole interview.
    """
    logger.info("Calling review function to get the review result...")
    model = ChatOpenAI(
        model=MODEL_NAME,
        api_key=api_key,
    )
    interview_transcript = _render_histories(histories)
    applicant_profile = APPLICANT_PROMPT.format(
        position=position,
        yoe=years_of_experience,
        cv=cv.strip(),
    )

    query_prompt = QUERY_PROMPT.format(
        applicant_profile=applicant_profile,
        interview_transcript=interview_transcript,
    )

    messages = [("system", REVIEWER_SYSTEM_PROMPT), ("human", query_prompt)]
    start_time = time.time()
    logger.info("Calling Reviewer LLM...")
    response = model.invoke(messages)
    end_time = time.time()
    logger.info(f"Reviewer LLM call took {end_time - start_time:.2f} seconds")
    # logger.info(f"Repsonse of reviewer: {response.content}")
    try:
        response_in_dict = json.loads(response.content)
    except json.decoder.JSONDecodeError:
        logger.error(f"Failed to decode JSON response from LLM: {response.content}")
        raise
    review_result = ReviewResult.model_validate(response_in_dict)
    return review_result


def _render_histories(histories: list[Union[HumanMessage, AIMessage]]) -> str:
    messages = []
    map_ = {
        "human": "applicant",
        "ai": "interviewer",
    }
    for message in histories:
        messages.append(f"{map_.get(message.type, message.type)}: {message.content}")
    return "\n".join(messages)
