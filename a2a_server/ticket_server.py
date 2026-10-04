import json
import os
import sys
from datetime import datetime
from zoneinfo import ZoneInfo

from langchain_core.prompts import ChatPromptTemplate
from python_a2a import A2AServer, AgentCard, AgentSkill, run_server

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
table_schema_string = common.load_sql_script("ticket_schema.sql")

TICKET_QUERY_URL = common.require_setting("TICKET_QUERY_URL", conf.ticket_query_url)
TICKET_AGENT_URL = common.require_setting("TICKET_AGENT_URL", conf.ticket_agent_url)
sql_prompt = ChatPromptTemplate.from_template(
    common.require_setting("TICKET_SQL_PROMPT", conf.ticket_sql_prompt)
)


def _query_type_from_sql(sql: str) -> str:
    lowered = sql.lower()
    if "train_tickets" in lowered:
        return "train"
    if "flight_tickets" in lowered:
        return "flight"
    if "concert_tickets" in lowered:
        return "concert"
    return ""


def get_ticket_info(sql: str) -> str:
    """Call the ticket MCP server and return its JSON text."""
    result_text = common.call_mcp_tool(TICKET_QUERY_URL, sql, "ticket")
    logger.info(f"Ticket query result: {result_text}")
    return result_text


agent_card = AgentCard(
    name="TicketQueryAssistant",
    description="Trains, flights, and concert seats.",
    url=TICKET_AGENT_URL,
    version="1.0.4",
    capabilities={"streaming": True, "memory": True},
    skills=[
        AgentSkill(
            name="Ticket search",
            description="Find trains, flights, or concert seats from a natural-language request.",
            examples=[
                "Train from Sydney to Melbourne on 2026-10-03, Economy",
                "Flight from Sydney to Melbourne on 2026-10-02, Economy",
                "Tame Impala concert in Sydney on 2026-10-16, VIP",
            ],
        )
    ],
)


class TicketQueryServer(A2AServer):
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
            output = common.strip_code_fence(output)
            logger.info(f"Raw LLM output: {output}")

            if output.startswith("{"):
                first_line, _, rest = output.partition("\n")
                if '"status"' in first_line and "input_required" in first_line:
                    return json.loads(first_line if first_line.endswith("}") else output)
                if '"type"' in first_line:
                    query_type = json.loads(first_line)["type"]
                    sql_query = " ".join(line.strip() for line in rest.splitlines() if line.strip())
                    return {"status": "sql", "type": query_type, "sql": sql_query}

            if output.upper().lstrip().startswith("SELECT"):
                query_type = _query_type_from_sql(output)
                if query_type:
                    return {"status": "sql", "type": query_type, "sql": output}

            logger.error(f"Unusable LLM output format: {output}")
            return {
                "status": "input_required",
                "message": "Please include the ticket type, the cities or venue, and a date.",
            }
        except Exception as error:
            logger.error(f"Failed to generate the SQL query: {error}")
            return {
                "status": "input_required",
                "message": "Please name a train, flight, or concert, plus the date.",
            }

    def handle_task(self, task):
        content = (task.message or {}).get("content", {})
        conversation = content.get("text", "") if isinstance(content, dict) else ""
        logger.info(f"Conversation and user question: {conversation}")

        try:
            generated = self.generate_sql_query(conversation)
            if generated.get("status") == "input_required":
                return common.ask_for_input(task, generated["message"])

            sql_query = generated["sql"].strip().rstrip(";")
            query_type = generated.get("type") or _query_type_from_sql(sql_query)
            logger.info(f"Generated SQL query: {sql_query} (type: {query_type})")
            if not sql_query.upper().startswith("SELECT"):
                return common.fail_task(task, "Please ask for a train, a flight, or a concert.")

            ticket_result = get_ticket_info(sql_query)
            response = common.parse_mcp_payload(ticket_result)
            logger.info(f"MCP response: {response}")
            lines = []
            if response.get("status") == "success":
                for row in response.get("data", []):
                    if query_type == "train":
                        lines.append(
                            f"{row['departure_city']} to {row['arrival_city']}, departing {row['departure_time']}. "
                            f"Train {row['train_number']}, {row['seat_type']}, "
                            f"{row['price']} AUD, {row['remaining_seats']} seats left."
                        )
                    elif query_type == "flight":
                        lines.append(
                            f"{row['departure_city']} to {row['arrival_city']}, departing {row['departure_time']}. "
                            f"Flight {row['flight_number']}, {row['cabin_type']}, "
                            f"{row['price']} AUD, {row['remaining_seats']} seats left."
                        )
                    elif query_type == "concert":
                        lines.append(
                            f"{row['artist']} at {row['venue']}, {row['city']}, {row['start_time']}. "
                            f"{row['ticket_type']}, {row['price']} AUD, {row['remaining_seats']} seats left."
                        )
            return common.finish_task(
                task,
                response,
                "\n".join(lines),
                "No tickets matched that search. Please check the cities, date, and seat type.",
                "The ticket search could not be completed. Please try again.",
            )
        except Exception as error:
            logger.error(f"Query failed: {error}")
            return common.fail_task(task, "The ticket search could not be completed. Please try again.")


if __name__ == "__main__":
    ticket_server = TicketQueryServer()
    print("\n=== Server information ===")
    print(f"Name: {ticket_server.agent_card.name}")
    print(f"Description: {ticket_server.agent_card.description}")
    print("\nSkills:")
    for skill in ticket_server.agent_card.skills:
        print(f"- {skill.name}: {skill.description}")
    host, port = listen_address(TICKET_AGENT_URL, "TICKET_AGENT_URL")
    run_server(ticket_server, host=host, port=port)
