import json
import os
import sys

import requests
from langchain_openai import ChatOpenAI
from python_a2a import AgentCard, AgentSkill, TaskState, TaskStatus

PROJECT_DIRECTORY = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_DIRECTORY not in sys.path:
    sys.path.insert(0, PROJECT_DIRECTORY)

from create_logger import logger


def require_setting(name, value):
    if not value or not str(value).strip():
        raise RuntimeError(f"Missing {name}. Add it to the .env file.")
    return value


def build_agent_card(card_data, url):
    skills = [
        AgentSkill(
            name=skill["name"],
            description=skill.get("description", ""),
            examples=skill.get("examples") or [],
        )
        for skill in card_data.get("skills", [])
    ]
    return AgentCard(
        name=card_data["name"],
        description=card_data.get("description", ""),
        url=url,
        version=card_data.get("version", "1.0.0"),
        capabilities=card_data.get("capabilities") or {"streaming": True, "memory": True},
        skills=skills,
    )


def make_llm(conf):
    return ChatOpenAI(
        model=conf.model_name,
        base_url=conf.base_url,
        api_key=conf.api_key,
        temperature=conf.llm_temperature,
    )


def strip_code_fence(text):
    cleaned = text.strip()
    if not cleaned.startswith("```"):
        return cleaned
    lines = cleaned.splitlines()
    if lines and lines[0].startswith("```"):
        lines = lines[1:]
    if lines and lines[-1].strip() == "```":
        lines = lines[:-1]
    return "\n".join(lines).strip()


def call_mcp_tool(url, sql, service_name, unavailable_message):
    try:
        response = requests.post(url, json={"sql": sql}, timeout=30)
        response.raise_for_status()
        payload = response.json()
        return payload["content"][0]["text"]
    except Exception as error:
        logger.error(f"{service_name} MCP query failed: {error}")
        return json.dumps(
            {
                "status": "error",
                "message": unavailable_message,
            }
        )


def parse_mcp_payload(result):
    return json.loads(result) if isinstance(result, str) else result


def finish_task(task, response, success_text, no_data_message, failed_message):
    if response.get("status") == "success":
        task.artifacts = [{"parts": [{"type": "text", "text": success_text or no_data_message}]}]
        task.status = TaskStatus(state=TaskState.COMPLETED)
    elif response.get("status") == "no_data":
        task.status = TaskStatus(
            state=TaskState.INPUT_REQUIRED,
            message={"role": "agent", "content": {"text": response.get("message", no_data_message)}},
        )
    else:
        task.status = TaskStatus(
            state=TaskState.FAILED,
            message={"role": "agent", "content": {"text": response.get("message", failed_message)}},
        )
    return task


def fail_task(task, message):
    task.status = TaskStatus(
        state=TaskState.FAILED,
        message={"role": "agent", "content": {"text": message}},
    )
    return task


def ask_for_input(task, message):
    task.status = TaskStatus(
        state=TaskState.INPUT_REQUIRED,
        message={"role": "agent", "content": {"text": message}},
    )
    return task
