import json
import os
import sys

import requests
from langchain_openai import ChatOpenAI
from python_a2a import TaskState, TaskStatus

PROJECT_DIRECTORY = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_DIRECTORY not in sys.path:
    sys.path.insert(0, PROJECT_DIRECTORY)

from create_logger import logger

SCRIPTS_DIRECTORY = os.path.join(PROJECT_DIRECTORY, "scripts")


def require_setting(name, value):
    if not value or not str(value).strip():
        raise RuntimeError(f"Missing {name}. Add it to the .env file.")
    return value


def load_sql_script(filename):
    """Read a SQL file from the scripts directory."""
    path = os.path.join(SCRIPTS_DIRECTORY, filename)
    with open(path, encoding="utf-8") as sql_file:
        return sql_file.read().strip()


def make_llm(conf):
    return ChatOpenAI(
        model=conf.model_name,
        base_url=conf.base_url,
        api_key=conf.api_key,
        temperature=0.1,
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


def call_mcp_tool(url, sql, service_name):
    """Post a SQL statement to an MCP tool and return its JSON text."""
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
                "message": "This service is temporarily unavailable. Please try again.",
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
