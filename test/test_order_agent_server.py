import asyncio
import os
import sys
import uuid

import requests
from python_a2a import A2AClient, Message, MessageRole, Task, TextContent

project_directory = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_directory not in sys.path:
    sys.path.insert(0, project_directory)

from config import Config
from create_logger import logger

conf = Config()
QUERY = "Book 1 Economy train from Sydney to Melbourne on 2026-10-03"


def _require_setting(name, value):
    if not value or not str(value).strip():
        raise RuntimeError(f"Missing {name}. Add it to the .env file.")
    return value


ORDER_AGENT_URL = _require_setting("ORDER_AGENT_URL", conf.order_agent_url)


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


def test_order_agent():
    try:
        health = requests.get(f"{ORDER_AGENT_URL}/a2a/health", timeout=5)
        health.raise_for_status()

        order_client = A2AClient(ORDER_AGENT_URL, timeout=180)
        card = order_client.agent_card
        if card.name != "TicketOrderAssistant":
            raise RuntimeError(f"Unexpected agent card: {card.name}")
        if card.skills:
            logger.info("Supported skills:")
            for skill in card.skills:
                logger.info(f"- {skill.name}: {skill.description}")
                if skill.examples:
                    logger.info(f"  Examples: {', '.join(skill.examples)}")

        message = Message(content=TextContent(text=QUERY), role=MessageRole.USER)
        task = Task(id="task-" + str(uuid.uuid4()), message=message.to_dict())
        result_task = asyncio.run(order_client.send_task_async(task))
        logger.info(f"Raw response: {result_task}")

        if _state_value(result_task.status.state) != "completed":
            raise RuntimeError(f"Ticket booking did not complete: {_status_text(result_task)}")

        result_text = _artifact_text(result_task)
        if "Sydney" not in result_text or "Train ticket booked successfully." not in result_text:
            raise RuntimeError(f"Expected a successful Sydney train booking, got: {result_text}")
        print(result_text)
    except requests.RequestException as error:
        return False
    except Exception as error:
        print(f"Ticket order agent test failed: {error}")
        return False
    return True


if __name__ == "__main__":
    print("Ticket order agent server client test")
    sys.exit(0 if test_order_agent() else 1)
