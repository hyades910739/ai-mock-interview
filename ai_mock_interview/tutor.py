import logging
import os
import time

import dotenv
from langchain_openai import ChatOpenAI

logger = logging.getLogger(__name__)

dotenv.load_dotenv(override=False)
TUTOR_MODEL_NAME = os.getenv("TUTOR_MODEL_NAME")

GRAMMAR_TUTOR_SYSTEM_PROMPT = """
You are a tutor that helps users improve their answers during a mock interview.

Given a user’s answer, rewrite it to:
- fix grammar and word choice
- improve clarity and fluency
- keep the original meaning and tone

Only modify what is necessary.  

Make sure your responses sound like natural spoken conversation, not like a written article. Use simple, casual language.

Wrap every changed or added word or phrase in:
<span class="correct"></span>

Example:
Input:
I used to work on a project that I need to build a recommendation system for our service.

Output:
I <span class="correct">worked</span> on a project <span class="correct">where I built</span> a recommendation system for our service.
"""

ANSWER_TUTOR_SYSTEM_PROMPT = """
You are a tutor that helps users improve their answers during a mock interview.

You will be given:
- a Question
- a User Answer

Your task is to rewrite the User Answer into a better response to the Question by:
- correcting mistakes
- improving clarity and technical accuracy
- making the answer more concise and natural

Keep the original meaning unless it is wrong, and use conversational language, avoiding complex grammar or difficult words.

Make sure your responses sound like natural spoken conversation, not like a written article. Use simple, casual language.

Return only the improved answer.
Do NOT include labels, explanations, or prefixes.

Input format:
Question: ...
Answer: ...
"""


class Tutor:
    def __init__(self, api_key: str):
        self.model = ChatOpenAI(
            model=TUTOR_MODEL_NAME,
            # temperature=0.7,
            api_key=api_key,
        )
        logger.debug("Tutor model initialized.")

    def improve_grammar(self, answer: str) -> str:
        messages = [("system", GRAMMAR_TUTOR_SYSTEM_PROMPT), ("human", answer)]
        logger.info("Calling Grammar Tutor LLM...")
        start_time = time.time()
        response = self.model.invoke(messages)
        end_time = time.time()
        logger.info(f"Grammar Tutor LLM call took {end_time - start_time:.2f} seconds")
        return response.content

    async def aimprove_grammar(self, answer: str) -> str:
        messages = [("system", GRAMMAR_TUTOR_SYSTEM_PROMPT), ("human", answer)]
        logger.info("Calling Grammar Tutor LLM...")
        start_time = time.time()
        response = await self.model.ainvoke(messages)
        end_time = time.time()
        logger.info(f"Grammar Tutor LLM call took {end_time - start_time:.2f} seconds")
        return response.content

    def improve_answer(self, question: str, answer: str) -> str:
        input_ = f"Question: {question}\nAnswer: {answer}"
        messages = [("system", ANSWER_TUTOR_SYSTEM_PROMPT), ("human", input_)]
        logger.info("Calling Answer Tutor LLM...")
        start_time = time.time()
        response = self.model.invoke(messages)
        end_time = time.time()
        logger.info(f"Answer Tutor LLM call took {end_time - start_time:.2f} seconds")
        return response.content

    async def aimprove_answer(self, question: str, answer: str) -> str:
        input_ = f"Question: {question}\nAnswer: {answer}"
        messages = [("system", ANSWER_TUTOR_SYSTEM_PROMPT), ("human", input_)]
        logger.info("Calling Answer Tutor LLM...")
        start_time = time.time()
        response = await self.model.ainvoke(messages)
        end_time = time.time()
        logger.info(f"Answer Tutor LLM call took {end_time - start_time:.2f} seconds")
        return response.content
