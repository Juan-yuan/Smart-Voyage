import asyncio
import os
import sys
import uuid

import requests
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.tools import tool
from python_a2a import A2AClient, A2AServer, Message, MessageRole, Task, TextContent, run_server

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

ORDER_MCP_URL = common.require_setting("ORDER_MCP_URL", conf.order_mcp_url).rstrip("/")
ORDER_AGENT_URL = common.require_setting("ORDER_AGENT_URL", conf.order_agent_url)
TICKET_AGENT_URL = common.require_setting("TICKET_AGENT_URL", conf.ticket_agent_url)
ORDER_SYSTEM_PROMPT = common.require_setting("ORDER_SYSTEM_PROMPT", conf.order_system_prompt)


def _call_order_tool(name: str, payload: dict) -> str:
    response = requests.post(f"{ORDER_MCP_URL}/tools/{name}", json=payload, timeout=30)
    response.raise_for_status()
    body = response.json()
    return body["content"][0]["text"]


@tool(conf.order_train_tool_name, description=conf.order_train_tool_description)
def order_train(departure_date: str, train_number: str, seat_type: str, number: int) -> str:
    return _call_order_tool(
        conf.order_train_tool_name,
        {
            "departure_date": departure_date,
            "train_number": train_number,
            "seat_type": seat_type,
            "number": int(number),
        },
    )


@tool(conf.order_flight_tool_name, description=conf.order_flight_tool_description)
def order_flight(departure_date: str, flight_number: str, seat_type: str, number: int) -> str:
    return _call_order_tool(
        conf.order_flight_tool_name,
        {
            "departure_date": departure_date,
            "flight_number": flight_number,
            "seat_type": seat_type,
            "number": int(number),
        },
    )


@tool(conf.order_concert_tool_name, description=conf.order_concert_tool_description)
def order_concert(start_date: str, artist: str, venue: str, seat_type: str, number: int) -> str:
    return _call_order_tool(
        conf.order_concert_tool_name,
        {
            "start_date": start_date,
            "artist": artist,
            "venue": venue,
            "seat_type": seat_type,
            "number": int(number),
        },
    )


ORDER_TOOLS = [order_train, order_flight, order_concert]
ORDER_TOOL_MAP = {item.name: item for item in ORDER_TOOLS}


def _message_text(message) -> str:
    content = getattr(message, "content", "")
    if isinstance(content, str):
        return content.strip()
    return str(content).strip()


def order_tickets(query: str) -> dict:
    try:
        response = llm.bind_tools(ORDER_TOOLS).invoke(
            [
                SystemMessage(content=ORDER_SYSTEM_PROMPT),
                HumanMessage(content=query),
            ]
        )
        tool_calls = getattr(response, "tool_calls", None) or []
        if not tool_calls:
            follow_up = _message_text(response) or conf.msg_booking_missing
            return {"status": "input_required", "message": follow_up}

        results = []
        for call in tool_calls:
            name = call.get("name")
            args = call.get("args") or {}
            logger.info(f"Calling order tool {name} with {args}")
            booking_tool = ORDER_TOOL_MAP.get(name)
            if booking_tool is None:
                logger.error(f"Unknown booking tool: {name}")
                return {"status": "error", "message": conf.msg_booking_unknown_tool}
            results.append(booking_tool.invoke(args))
        return {"status": "success", "message": "\n".join(results)}
    except Exception as error:
        logger.error(f"Ticket booking failed: {error}")
        return {"status": "error", "message": conf.msg_booking_failed}


def _status_text(task) -> str:
    message = task.status.message or {}
    content = message.get("content", {}) if isinstance(message, dict) else {}
    if isinstance(content, dict) and content.get("text"):
        return content["text"]
    return str(message)


def _state_value(state) -> str:
    return state.value if hasattr(state, "value") else str(state)


agent_card = common.build_agent_card(conf.order_agent_card, ORDER_AGENT_URL)


class TicketOrderServer(A2AServer):
    def __init__(self):
        super().__init__(agent_card=agent_card)
        self.llm = llm
        self.ticket_client = A2AClient(TICKET_AGENT_URL, timeout=conf.agent_timeout_seconds)

    def handle_task(self, task):
        content = (task.message or {}).get("content", {})
        conversation = content.get("text", "") if isinstance(content, dict) else ""
        logger.info(f"Booking request: {conversation}")

        try:
            message_ticket = Message(content=TextContent(text=conversation), role=MessageRole.USER)
            task_ticket = Task(id="task-" + str(uuid.uuid4()), message=message_ticket.to_dict())
            ticket_result_task = asyncio.run(self.ticket_client.send_task_async(task_ticket))
            logger.info(f"Raw availability response: {ticket_result_task}")

            if _state_value(ticket_result_task.status.state) != "completed":
                required_message = _status_text(ticket_result_task)
                logger.info(f"Availability was not found: {required_message}")
                return common.ask_for_input(task, required_message)

            ticket_result = ticket_result_task.artifacts[0]["parts"][0]["text"]
            logger.info(f"Availability: {ticket_result}")

            order_result = order_tickets(f"{conversation}\nAvailability:\n{ticket_result}")

            data = order_result.get("message", "")
            if order_result.get("status") == "input_required":
                return common.ask_for_input(task, data)
            if order_result.get("status") != "success":
                return common.fail_task(task, data or conf.msg_booking_failed)

            result = f"{data.strip()}\n\n{ticket_result.strip()}"
            return common.finish_task(
                task,
                {"status": "success"},
                result,
                conf.msg_booking_none,
                conf.msg_booking_failed,
            )
        except Exception as error:
            logger.error(f"Booking failed: {error}")
            return common.fail_task(task, conf.msg_booking_failed)


if __name__ == "__main__":
    order_server = TicketOrderServer()
    for skill in order_server.agent_card.skills:
        print(f"- {skill.name}: {skill.description}")
    host, port = listen_address(ORDER_AGENT_URL, "ORDER_AGENT_URL")
    run_server(order_server, host=host, port=port)
