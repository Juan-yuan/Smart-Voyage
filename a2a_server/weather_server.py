import json
import os
import sys
from datetime import datetime
from urllib.parse import urlparse
from zoneinfo import ZoneInfo

import requests
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from python_a2a import A2AServer, AgentCard, AgentSkill, TaskState, TaskStatus, run_server

project_directory = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_directory not in sys.path:
    sys.path.insert(0, project_directory)

from config import Config
from create_logger import logger

conf = Config()

llm = ChatOpenAI(
    model=conf.model_name,
    base_url=conf.base_url,
    api_key=conf.api_key,
    temperature=0.1,
)

# SQL schema passed to the prompt so the model queries weather_data correctly.
table_schema_string = """
CREATE TABLE IF NOT EXISTS weather_data (
    id INT AUTO_INCREMENT PRIMARY KEY,
    city VARCHAR(50) NOT NULL COMMENT 'City name',
    fx_date DATE NOT NULL COMMENT 'Forecast date',
    sunrise TIME COMMENT 'Sunrise time',
    sunset TIME COMMENT 'Sunset time',
    moonrise TIME COMMENT 'Moonrise time',
    moonset TIME COMMENT 'Moonset time',
    moon_phase VARCHAR(20) COMMENT 'Moon phase name',
    moon_phase_icon VARCHAR(10) COMMENT 'Moon phase icon code',
    temp_max INT COMMENT 'Maximum temperature',
    temp_min INT COMMENT 'Minimum temperature',
    icon_day VARCHAR(10) COMMENT 'Daytime weather icon code',
    text_day VARCHAR(20) COMMENT 'Daytime weather description',
    icon_night VARCHAR(10) COMMENT 'Nighttime weather icon code',
    text_night VARCHAR(20) COMMENT 'Nighttime weather description',
    wind360_day INT COMMENT 'Daytime wind direction in degrees',
    wind_dir_day VARCHAR(20) COMMENT 'Daytime wind direction',
    wind_scale_day VARCHAR(10) COMMENT 'Daytime wind scale',
    wind_speed_day INT COMMENT 'Daytime wind speed (km/h)',
    wind360_night INT COMMENT 'Nighttime wind direction in degrees',
    wind_dir_night VARCHAR(20) COMMENT 'Nighttime wind direction',
    wind_scale_night VARCHAR(10) COMMENT 'Nighttime wind scale',
    wind_speed_night INT COMMENT 'Nighttime wind speed (km/h)',
    precip DECIMAL(5,1) COMMENT 'Precipitation (mm)',
    uv_index INT COMMENT 'UV index',
    humidity INT COMMENT 'Relative humidity (%)',
    pressure INT COMMENT 'Atmospheric pressure (hPa)',
    vis INT COMMENT 'Visibility (km)',
    cloud INT COMMENT 'Cloud cover (%)',
    update_time DATETIME COMMENT 'Data update time',
    UNIQUE KEY unique_city_date (city, fx_date)
) ENGINE=INNODB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Weather data table';
"""

def _require_setting(name, value):
    if not value or not str(value).strip():
        raise RuntimeError(f"Missing {name}. Add it to the .env file.")
    return value


WEATHER_MCP_URL = _require_setting("WEATHER_MCP_URL", conf.weather_mcp_url)
WEATHER_AGENT_URL = _require_setting("WEATHER_AGENT_URL", conf.weather_agent_url)
sql_prompt = ChatPromptTemplate.from_template(
    _require_setting("WEATHER_SQL_PROMPT", conf.weather_sql_prompt)
)


def _strip_code_fence(text: str) -> str:
    cleaned = text.strip()
    if not cleaned.startswith("```"):
        return cleaned
    lines = cleaned.splitlines()
    if lines and lines[0].startswith("```"):
        lines = lines[1:]
    if lines and lines[-1].strip() == "```":
        lines = lines[:-1]
    return "\n".join(lines).strip()


def get_weather(sql: str) -> str:
    """Call the weather MCP server and return its JSON text."""
    try:
        response = requests.post(WEATHER_MCP_URL, json={"sql": sql}, timeout=30)
        response.raise_for_status()
        payload = response.json()
        result_text = payload["content"][0]["text"]
        logger.info(f"Weather query result: {result_text}")
        return result_text
    except Exception as error:
        logger.error(f"Weather MCP query failed: {error}")
        return json.dumps(
            {
                "status": "error",
                "message": "Could not reach the weather MCP server. Start the weather MCP server first.",
            }
        )


agent_card = AgentCard(
    name="WeatherQueryAssistant",
    description="Weather query assistant that answers natural-language questions from the weather_data table.",
    url=WEATHER_AGENT_URL,
    version="1.0.0",
    capabilities={"streaming": True, "memory": True},
    skills=[
        AgentSkill(
            name="execute weather query",
            description="Run a weather query and return rows from the weather database. Accepts natural language.",
            examples=["Sydney weather on 2026-10-02", "Melbourne for the next 5 days", "What is the weather today"],
        )
    ],
)


class WeatherQueryServer(A2AServer):
    def __init__(self):
        super().__init__(agent_card=agent_card)
        self.llm = llm
        self.sql_prompt = sql_prompt
        self.schema = table_schema_string

    def generate_sql_query(self, conversation: str) -> dict:
        """Turn a conversation into SQL, or a follow-up question when details are missing."""
        try:
            chain = self.sql_prompt | self.llm
            current_date = datetime.now(ZoneInfo("Australia/Sydney")).strftime("%Y-%m-%d")
            output = chain.invoke(
                {
                    "conversation": conversation,
                    "current_date": current_date,
                    "table_schema_string": self.schema,
                }
            ).content.strip()
            output = _strip_code_fence(output)
            logger.info(f"Raw LLM output: {output}")
            if output.startswith("{"):
                return json.loads(output)
            return {"status": "sql", "sql": output}
        except Exception as error:
            logger.error(f"Failed to generate the SQL query: {error}")
            return {
                "status": "input_required",
                "message": "The query is invalid. Please provide a city and a date.",
            }

    def handle_task(self, task):
        content = (task.message or {}).get("content", {})
        conversation = content.get("text", "") if isinstance(content, dict) else ""
        logger.info(f"Conversation and user question: {conversation}")

        try:
            sql_result = self.generate_sql_query(conversation)
            if sql_result.get("status") == "input_required":
                task.status = TaskStatus(
                    state=TaskState.INPUT_REQUIRED,
                    message={"role": "agent", "content": {"text": sql_result["message"]}},
                )
                return task

            sql_query = sql_result["sql"].strip().rstrip(";")
            logger.info(f"Generated SQL query: {sql_query}")
            if not sql_query.upper().startswith("SELECT"):
                task.status = TaskStatus(
                    state=TaskState.FAILED,
                    message={
                        "role": "agent",
                        "content": {"text": "Only SELECT queries are allowed. Please ask a weather question."},
                    },
                )
                return task

            weather_result = get_weather(sql_query)
            response = json.loads(weather_result) if isinstance(weather_result, str) else weather_result
            logger.info(f"MCP response: {response}")

            if response.get("status") == "success":
                data = response.get("data", [])
                response_text = "\n".join(
                    (
                        f"{row['city']} {row['fx_date']}: {row['text_day']} (night: {row['text_night']}), "
                        f"temperature {row['temp_min']}-{row['temp_max']}°C, humidity {row['humidity']}%, "
                        f"wind {row['wind_dir_day']}, precipitation {row['precip']}mm"
                    )
                    for row in data
                )
                task.artifacts = [{"parts": [{"type": "text", "text": response_text}]}]
                task.status = TaskStatus(state=TaskState.COMPLETED)
            elif response.get("status") == "no_data":
                response_text = response.get("message", "Please enter another city and date.")
                task.status = TaskStatus(
                    state=TaskState.INPUT_REQUIRED,
                    message={"role": "agent", "content": {"text": response_text}},
                )
            else:
                response_text = response.get("message", "Query failed. Please try again or provide more detail.")
                task.status = TaskStatus(
                    state=TaskState.FAILED,
                    message={"role": "agent", "content": {"text": response_text}},
                )
            return task
        except Exception as error:
            logger.error(f"Query failed: {error}")
            task.status = TaskStatus(
                state=TaskState.FAILED,
                message={
                    "role": "agent",
                    "content": {"text": f"Query failed: {error}. Please try again or provide more detail."},
                },
            )
            return task


if __name__ == "__main__":
    weather_server = WeatherQueryServer()
    for skill in weather_server.agent_card.skills:
        print(f"- {skill.name}: {skill.description}")
    parsed_url = urlparse(WEATHER_AGENT_URL)
    run_server(
        weather_server,
        host=parsed_url.hostname or "127.0.0.1",
        port=parsed_url.port or 5005,
    )
