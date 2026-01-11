from typing import Any, Union, Literal

from langchain.agents import AgentState, create_agent
from langchain.agents.middleware import before_model
from langchain.messages import RemoveMessage
from langchain_core.chat_history import InMemoryChatMessageHistory
from langchain_core.messages import trim_messages
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables import RunnableConfig
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph.message import REMOVE_ALL_MESSAGES
from langgraph.runtime import Runtime
from langgraph.store.memory import InMemoryStore
from langgraph.types import StateSnapshot
from pydantic import BaseModel
import os
import dotenv

dotenv.load_dotenv(override=False)

# model = ChatOpenAI(name="gpt-5-nano-2025-08-07")
# INTERVIEWER_MODEL_NAME = "gpt-5-nano-2025-08-07"
INTERVIEWER_MODEL_NAME = os.getenv("INTERVIEWER_MODEL_NAME")

TECHNICAL_INTERVIEW_INTERVIEWER_SYSTEM_PROMPT = """
You are an interviewer responsible for conducting a technical interview with a candidate. Follow these rules:

* You are an interviewer, so chat like a real human, and replay conversation, not articles.
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
) -> str:
    if interview_type == "Technical":
        user_profile = USER_PROFILE_SYSTEM_PROMPT.format(
            name=name, position=position, yoe=years_of_experience, cv=cv.strip()
        )
        return TECHNICAL_INTERVIEW_INTERVIEWER_SYSTEM_PROMPT + user_profile
    else:
        raise NotImplementedError()


@before_model
def trim_messages(state: InterviewerAgentState, runtime: Runtime) -> dict[str, Any] | None:
    """Keep only the last few messages to fit context window."""
    messages = state["messages"]

    # if len(messages) <= 3:
    #     return None  # No changes needed

    # first_msg = messages[0]
    # recent_messages = messages[-3:] if len(messages) % 2 == 0 else messages[-4:]
    # new_messages = [first_msg] + recent_messages

    # return {
    #     "messages": [
    #         RemoveMessage(id=REMOVE_ALL_MESSAGES),
    #         *new_messages
    #     ]
    # }
    print(type(state))
    print(state["messages"])
    print(state.keys())
    print("----")
    return


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


{
    "name": "Eric",
    "position": "MLE",
    "years_of_experience": 4.0,
    "interview_type": "Technical",
    "openai_api_key": "111",
    "cv_path": "uploads/a120d158-6c60-4631-98e6-a1e0cf6b9a08_resume-20251211.pdf",
    "enable_voice": False,
    "enable_advice": True,
}


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
        )
        print("system_prompt: ")
        print(self.system_prompt)
        model = ChatOpenAI(name=INTERVIEWER_MODEL_NAME, temperature=0.7, api_key=api_key)
        self.agent = create_agent(
            model,
            checkpointer=self.memory,
            state_schema=InterviewerAgentState,
            middleware=[trim_human_messages],
            system_prompt=self.system_prompt,
        )

    def chat(self, user_input: str, session_id: str) -> InterviewerResponse:
        response = self.agent.invoke(
            {
                "messages": [{"role": "user", "content": user_input}],
            },
            config={"configurable": {"thread_id": session_id}},
        )
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
