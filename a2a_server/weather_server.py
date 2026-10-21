import json
import os
import sys
from datetime import datetime
from zoneinfo import ZoneInfo

from langchain_core.prompts import ChatPromptTemplate
from python_a2a import A2AServer, run_server

server_directory = os.path.dirname(os.path.abspath(__file__))
project_directory = os.path.dirname(server_directory)
for path in (server_directory, project_directory):
    if path not in sys.path:
        sys.path.insert(0, path)

import common
from config import Config, listen_address
from create_logger import logger

conf = Config()
llm = common.make_llm(conf)
table_schema_string = common.require_setting("WEATHER_SCHEMA_SQL", conf.weather_schema_sql)

WEATHER_MCP_URL = common.require_setting("WEATHER_MCP_URL", conf.weather_mcp_url)
WEATHER_AGENT_URL = common.require_setting("WEATHER_AGENT_URL", conf.weather_agent_url)
sql_prompt = ChatPromptTemplate.from_template(
    common.require_setting("WEATHER_SQL_PROMPT", conf.weather_sql_prompt)
)


def get_weather(sql: str) -> str:
    result_text = common.call_mcp_tool(
        WEATHER_MCP_URL,
        sql,
        "weather",
        conf.msg_service_unavailable,
    )
    logger.info(f"Weather query result: {result_text}")
    return result_text


agent_card = common.build_agent_card(conf.weather_agent_card, WEATHER_AGENT_URL)


class WeatherQueryServer(A2AServer):
    def __init__(self):
        super().__init__(agent_card=agent_card)
        self.llm = llm
        self.sql_prompt = sql_prompt
        self.schema = table_schema_string

    def generate_sql_query(self, conversation: str) -> dict:
        try:
            chain = self.sql_prompt | self.llm
            current_date = datetime.now(ZoneInfo(conf.app_timezone)).strftime("%Y-%m-%d")
            raw_content = chain.invoke(
                {
                    "conversation": conversation,
                    "current_date": current_date,
                    "table_schema_string": self.schema,
                }
            ).content
            output = raw_content if isinstance(raw_content, str) else str(raw_content)
            output = common.strip_code_fence(output)
            logger.info(f"Raw LLM output: {output}")
            if output.startswith("{"):
                return json.loads(output)
            return {"status": "sql", "sql": output}
        except Exception as error:
            logger.error(f"Failed to generate the SQL query: {error}")
            return {
                "status": "input_required",
                "message": conf.msg_weather_need_city_date,
            }

    def handle_task(self, task):
        content = (task.message or {}).get("content", {})
        conversation = content.get("text", "") if isinstance(content, dict) else ""
        logger.info(f"Conversation and user question: {conversation}")

        try:
            sql_result = self.generate_sql_query(conversation)
            if sql_result.get("status") == "input_required":
                return common.ask_for_input(task, sql_result["message"])

            sql_query = sql_result["sql"].strip().rstrip(";")
            logger.info(f"Generated SQL query: {sql_query}")
            if not sql_query.upper().startswith("SELECT"):
                return common.fail_task(task, conf.msg_weather_ask_select)

            weather_result = get_weather(sql_query)
            response = common.parse_mcp_payload(weather_result)
            logger.info(f"MCP response: {response}")
            if response.get("status") == "success":
                data = response.get("data", [])
                response_text = "\n".join(
                    conf.weather_row_template.format(**row) for row in data
                )
            else:
                response_text = ""
            return common.finish_task(
                task,
                response,
                response_text,
                conf.msg_weather_no_data,
                conf.msg_weather_failed,
            )
        except Exception as error:
            logger.error(f"Query failed: {error}")
            return common.fail_task(task, conf.msg_weather_failed)


if __name__ == "__main__":
    weather_server = WeatherQueryServer()
    for skill in weather_server.agent_card.skills:
        print(f"- {skill.name}: {skill.description}")
    host, port = listen_address(WEATHER_AGENT_URL, "WEATHER_AGENT_URL")
    run_server(weather_server, host=host, port=port)
