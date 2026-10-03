import asyncio
import os
import sys
import uuid

import requests
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from python_a2a import A2AClient, Message, MessageRole, Task, TextContent

project_directory = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_directory not in sys.path:
    sys.path.insert(0, project_directory)

from config import Config
from create_logger import logger

conf = Config()
QUERY = "Train from Sydney to Melbourne on 2026-10-03, Economy"


def _require_setting(name, value):
    if not value or not str(value).strip():
        raise RuntimeError(f"Missing {name}. Add it to the .env file.")
    return value


TICKET_AGENT_URL = _require_setting("TICKET_AGENT_URL", conf.ticket_agent_url)

llm = ChatOpenAI(
    model=conf.model_name,
    api_key=conf.api_key,
    base_url=conf.base_url,
    temperature=0.1,
)

ticket_prompt = ChatPromptTemplate.from_template(
    _require_setting("TICKET_SUMMARY_PROMPT", conf.ticket_summary_prompt)
)


def _state_value(state) -> str:
    return state.value if hasattr(state, "value") else str(state)


def _artifact_text(task) -> str:
    artifacts = task.artifacts or []
    return artifacts[0]["parts"][0]["text"]


def _status_text(task) -> str:
    message = task.status.message or {}
    content = message.get("content", {}) if isinstance(message, dict) else {}
    if isinstance(content, dict) and content.get("text"):
        return content["text"]
    return str(message)


def test_ticket_agent():
    try:
        health = requests.get(f"{TICKET_AGENT_URL}/a2a/health", timeout=5)
        health.raise_for_status()
        logger.info("Connected to the ticket agent.")

        ticket_client = A2AClient(TICKET_AGENT_URL, timeout=120)
        card = ticket_client.agent_card
        logger.info("Fetched ticket assistant information")
        logger.info(f"Name: {card.name}")
        logger.info(f"Description: {card.description}")
        logger.info(f"Version: {card.version}")
        if card.name != "TicketQueryAssistant":
            raise RuntimeError(f"Unexpected agent card: {card.name}")
        if card.skills:
            logger.info("Supported skills:")
            for skill in card.skills:
                logger.info(f"- {skill.name}: {skill.description}")
                if skill.examples:
                    logger.info(f"  Examples: {', '.join(skill.examples)}")

        logger.info(f"User query (tickets): {QUERY}")
        message_ticket = Message(content=TextContent(text=QUERY), role=MessageRole.USER)
        task_ticket = Task(id="task-" + str(uuid.uuid4()), message=message_ticket.to_dict())
        ticket_result_task = asyncio.run(ticket_client.send_task_async(task_ticket))
        logger.info(f"Raw response: {ticket_result_task}")

        if _state_value(ticket_result_task.status.state) != "completed":
            raise RuntimeError(f"Ticket query did not complete: {_status_text(ticket_result_task)}")

        ticket_result = _artifact_text(ticket_result_task)
        if "Sydney" not in ticket_result or "Melbourne" not in ticket_result:
            raise RuntimeError(f"Expected a Sydney to Melbourne train, got: {ticket_result}")

        summary_chain = ticket_prompt | llm
        summary = summary_chain.invoke({"tickets": ticket_result}).content.strip()
        if not summary:
            raise RuntimeError("The ticket summary was empty.")
        logger.info(f"**Ticket presenter summary**:\n{summary}")
        print(summary)
    except requests.RequestException as error:
        print(f"Ticket agent test failed: {error}")
        return False
    except Exception as error:
        logger.error(f"Ticket agent test failed: {error}")
        print(f"Ticket agent test failed: {error}")
        return False
    return True


if __name__ == "__main__":
    print("Ticket agent server query client test")
    sys.exit(0 if test_ticket_agent() else 1)
