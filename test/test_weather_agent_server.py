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

from config import Config, service_origin
from create_logger import logger

conf = Config()
AGENT_URL = service_origin(conf.weather_agent_url, "WEATHER_AGENT_URL")
QUERY = "Sydney weather on 2026-09-28"

llm = ChatOpenAI(
    model=conf.model_name,
    api_key=conf.api_key,
    base_url=conf.base_url,
    temperature=0.1,
)

def _require_setting(name, value):
    if not value or not str(value).strip():
        raise RuntimeError(f"Missing {name}. Add it to the .env file.")
    return value


weather_prompt = ChatPromptTemplate.from_template(
    _require_setting("WEATHER_TEST_SUMMARY_PROMPT", conf.weather_test_summary_prompt)
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


def test_weather_agent():
    try:
        health = requests.get(f"{AGENT_URL}/a2a/health", timeout=5)
        health.raise_for_status()
        logger.info("Connected to the weather agent.")

        weather_client = A2AClient(AGENT_URL, timeout=120)
        card = weather_client.agent_card
        logger.info("Fetched weather assistant information")
        logger.info(f"Name: {card.name}")
        logger.info(f"Description: {card.description}")
        logger.info(f"Version: {card.version}")
        if card.name != "WeatherQueryAssistant":
            raise RuntimeError(f"Unexpected agent card: {card.name}")
        if card.skills:
            logger.info("Supported skills:")
            for skill in card.skills:
                logger.info(f"- {skill.name}: {skill.description}")
                if skill.examples:
                    logger.info(f"  Examples: {', '.join(skill.examples)}")

        logger.info(f"User query (weather): {QUERY}")
        message_weather = Message(content=TextContent(text=QUERY), role=MessageRole.USER)
        task_weather = Task(id="task-" + str(uuid.uuid4()), message=message_weather.to_dict())
        weather_result_task = asyncio.run(weather_client.send_task_async(task_weather))
        logger.info(f"Raw response: {weather_result_task}")

        if _state_value(weather_result_task.status.state) != "completed":
            raise RuntimeError(f"Weather query did not complete: {_status_text(weather_result_task)}")

        weather_result = _artifact_text(weather_result_task)
        if "Sydney" not in weather_result:
            raise RuntimeError(f"Expected Sydney weather text, got: {weather_result}")

        summary_chain = weather_prompt | llm
        summary = summary_chain.invoke({"weather": weather_result}).content.strip()
        if not summary:
            raise RuntimeError("The weather summary was empty.")
        logger.info(f"**Weather presenter summary**:\n{summary}")
        print(summary)
    except requests.RequestException as error:
        print("Start the weather agent from WEATHER_AGENT_URL first.")
        print(f"Weather agent test failed: {error}")
        return False
    except Exception as error:
        logger.error(f"Weather agent test failed: {error}")
        print(f"Weather agent test failed: {error}")
        return False
    return True


if __name__ == "__main__":
    print("Weather agent server query client test")
    sys.exit(0 if test_weather_agent() else 1)
