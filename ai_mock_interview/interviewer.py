import logging
import os
import time
from typing import Any, Literal, Union

import dotenv
from langchain.agents import AgentState, create_agent
from langchain.agents.middleware import before_model
from langchain.messages import RemoveMessage
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph.message import REMOVE_ALL_MESSAGES
from langgraph.runtime import Runtime
from pydantic import BaseModel

logger = logging.getLogger(__name__)

dotenv.load_dotenv(override=False)

INTERVIEWER_MODEL_NAME = os.getenv("INTERVIEWER_MODEL_NAME")

BEHAVIORAL_INTERVIEW_INTERVIEWER_SYSTEM_PROMPT = """
You are an interviewer responsible for conducting a behavioral interview with a candidate. Follow these rules:

* You are an interviewer, so chat like a real human, reply in conversation form, not articles. Don't add any prefix or title.
* {interviewer_personality_prompt}
* This is a behavioral interview. Focus on questions about the candidate’s past experiences, communication style, teamwork, problem-solving, leadership, and how they handle challenges or conflict.
* If the interviewee’s resume is available, ask questions based on their previous roles, responsibilities, and workplace situations.
* If the interviewee’s years of experience are available, adjust the depth and complexity of the questions to match their experience level.
* Encourage the interviewee to answer using real examples (for example, using STAR: Situation, Task, Action, Result), but do not explicitly mention the framework unless needed.
* You may ask follow-up questions based on the interviewee’s answers, but do not ask more than 5 questions on a single topic.
* You may briefly summarize the interviewee’s answers, but you must always ask exactly one question at a time during the conversation.
* You may also ask common behavioral interview questions (for example, “Tell me about a time you handled a difficult teammate.”).

"""

TECHNICAL_INTERVIEW_INTERVIEWER_SYSTEM_PROMPT = """
You are an interviewer responsible for conducting a technical interview with a candidate. Follow these rules:

* You are an interviewer, so chat like a real human, reply in conversation form, not articles. Don't add any prefix or title.
* {interviewer_personality_prompt}
* This is a technical interview. Focus on technical questions relevant to the job title and the interviewee’s background.
* If the interviewee’s resume is available, ask questions based on their previous work experience or projects.
* If the interviewee’s years of experience are available, tailor the difficulty and depth of the questions to match their experience level.
* You may ask follow-up questions based on the interviewee’s answers, but do not ask more than 5 questions on a single topic.
* You may briefly summarize the interviewee’s answers, but you must always ask exactly one question at a time during the conversation.
* You may also ask common technical questions related to the job title (for example, “What is overfitting?” for a Data Scientist role).
"""

USER_PROFILE_SYSTEM_PROMPT = """
# Interviewee's Profile:
* Name: {name}
* Position: {position}
* Years of experience {yoe}
* CV: 
```
{cv}
```
"""
INTERVIEWER_PERSONALITY_SYSTEM_PROMPT_FACTORY = {
    "strict": "You are a strict interviewer who challenges the interviewee’s answers to probe their depth of understanding and frequently asks difficult, in-depth questions.",
    "friendly": "You are a friendly interviewer who is supportive and encouraging toward the interviewee.",
}


N_HUMAN_MESSAGES_TO_KEEP = 5


class InterviewerResponse(BaseModel):
    index: int
    content: str


class InterviewerAgentState(AgentState):
    user_name: str
    position: str
    years_of_experience: float
    user_cv: str | None


def interviewer_system_prompt_factory(
    interview_type: Literal["Behavioral", "Technical"],
    name: str,
    position: str,
    years_of_experience: float,
    cv: str,
    interviewer_personality: str,
) -> str:
    if interviewer_personality not in INTERVIEWER_PERSONALITY_SYSTEM_PROMPT_FACTORY:
        raise ValueError(f"Invalid interviewer personality: {interviewer_personality}")
    interviewer_personality_prompt = INTERVIEWER_PERSONALITY_SYSTEM_PROMPT_FACTORY[interviewer_personality].strip()

    user_profile = USER_PROFILE_SYSTEM_PROMPT.format(
        name=name,
        position=position,
        yoe=years_of_experience,
        cv=cv.strip(),
        # interviewer_personality_prompt=interviewer_personality_prompt,
    )

    if interview_type == "Technical":
        return (
            TECHNICAL_INTERVIEW_INTERVIEWER_SYSTEM_PROMPT.format(
                interviewer_personality_prompt=interviewer_personality_prompt
            )
            + user_profile
        )
    elif interview_type == "Behavioral":
        return (
            BEHAVIORAL_INTERVIEW_INTERVIEWER_SYSTEM_PROMPT.format(
                interviewer_personality_prompt=interviewer_personality_prompt
            )
            + user_profile
        )
    else:
        raise ValueError(f"Invalid interview type: {interview_type}")


@before_model
def trim_human_messages(state: InterviewerAgentState, runtime: Runtime) -> dict[str, Any] | None:
    """Keep only the last few messages to fit context window."""
    messages = state["messages"]

    if len(messages) < 2:
        return None  # No changes needed

    # ai_message_ids = [m.id for m in messages if m.type == 'ai']
    human_message_ids = [m.id for m in messages if m.type == "human"]
    if len(human_message_ids) <= N_HUMAN_MESSAGES_TO_KEEP:
        return None

    new_messages = [RemoveMessage(id=i) for i in human_message_ids[:-N_HUMAN_MESSAGES_TO_KEEP]]
    return {"messages": new_messages}


class Interviewer:
    def __init__(self, config: dict):
        self.message_historys = []
        self.memory = InMemorySaver()
        api_key = config.get("openai_api_key")

        self.system_prompt = interviewer_system_prompt_factory(
            interview_type=config["interview_type"],
            name=config["name"],
            position=config["position"],
            years_of_experience=config["years_of_experience"],
            cv=config["cv_str"],
            interviewer_personality=config["interviewer_personality"],
        )
        model = ChatOpenAI(name=INTERVIEWER_MODEL_NAME, temperature=0.7, api_key=api_key)
        self.agent = create_agent(
            model,
            checkpointer=self.memory,
            state_schema=InterviewerAgentState,
            middleware=[trim_human_messages],
            system_prompt=self.system_prompt,
        )
        logger.info("Successfully generate interviewer agent.")
        logger.info(f"System prompt:\n {self.system_prompt}")

    def chat(self, user_input: str, session_id: str) -> InterviewerResponse:
        logger.info("Calling Interviewer agent...")
        start_time = time.time()
        response = self.agent.invoke(
            {
                "messages": [{"role": "user", "content": user_input}],
            },
            config={"configurable": {"thread_id": session_id}},
        )
        end_time = time.time()
        logger.info(f"Interviewer agent call took {end_time - start_time:.2f} seconds")
        current_index = len(self.message_historys) // 2 + 1
        # update history
        latest_conversation = response["messages"][-2:]
        for message in latest_conversation:
            self.message_historys.append(message)
        # self.save_history(session_id)
        text_content = response["messages"][-1].content
        return InterviewerResponse(index=current_index, content=text_content)

    async def achat(self, user_input: str, session_id: str) -> InterviewerResponse:
        logger.info("Calling Interviewer agent...")
        start_time = time.time()
        response = await self.agent.ainvoke(
            {
                "messages": [{"role": "user", "content": user_input}],
            },
            config={"configurable": {"thread_id": session_id}},
        )
        end_time = time.time()
        logger.info(f"Interviewer agent call took {end_time - start_time:.2f} seconds")
        current_index = len(self.message_historys) // 2 + 1
        # update history
        latest_conversation = response["messages"][-2:]
        for message in latest_conversation:
            self.message_historys.append(message)
        # self.save_history(session_id)
        text_content = response["messages"][-1].content
        return InterviewerResponse(index=current_index, content=text_content)

    def save_history(self, session_id: str):
        with open(f"history_{session_id}.txt", "w") as f:
            for m in self.message_historys:
                f.writelines(f"{m.type:<6}: {m.content}\n" + "-" * 20)
