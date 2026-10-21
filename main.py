import asyncio
import json
import os
import re
import sys
import uuid
from datetime import datetime
from zoneinfo import ZoneInfo

from langchain_openai import ChatOpenAI
from python_a2a import A2AClient, AgentNetwork, Message, MessageRole, Task, TextContent

project_directory = os.path.dirname(os.path.abspath(__file__))
if project_directory not in sys.path:
    sys.path.insert(0, project_directory)

from config import Config
from create_logger import logger
from main_prompts import SmartVoyagePrompts

conf = Config()

messages = []
agent_network = None
llm = None
agent_urls = {}
conversation_history = ""


def _require_setting(name, value):
    if not value or not str(value).strip():
        raise RuntimeError(f"Missing {name}. Add it to the .env file.")
    return value


def _text(content) -> str:
    if isinstance(content, str):
        return content.strip()
    return str(content).strip()


def _state_value(state) -> str:
    return state.value if hasattr(state, "value") else str(state)


def _status_text(task) -> str:
    message = task.status.message or {}
    content = message.get("content", {}) if isinstance(message, dict) else {}
    if isinstance(content, dict) and content.get("text"):
        return content["text"]
    return str(message)


def resolve_route(intent):
    return conf.intent_agent_map.get(intent)


def initialize_system():
    global agent_network, llm, agent_urls, conversation_history

    agent_urls = {
        "WeatherQueryAssistant": _require_setting("WEATHER_AGENT_URL", conf.weather_agent_url),
        "TicketQueryAssistant": _require_setting("TICKET_AGENT_URL", conf.ticket_agent_url),
        "TicketOrderAssistant": _require_setting("ORDER_AGENT_URL", conf.order_agent_url),
    }
    network = AgentNetwork(name=conf.network_name)
    for name, url in agent_urls.items():
        network.add(name, A2AClient(url, timeout=conf.agent_timeout_seconds))
    agent_network = network

    llm = ChatOpenAI(
        model=conf.model_name,
        api_key=conf.api_key,
        base_url=conf.base_url,
        temperature=conf.llm_temperature,
    )
    conversation_history = ""


def intent_agent(user_input):
    global conversation_history, llm

    chain = SmartVoyagePrompts.intent_prompt() | llm
    current_date = datetime.now(ZoneInfo(conf.app_timezone)).strftime("%Y-%m-%d")
    recent_history = "\n".join(conversation_history.split("\n")[-conf.history_intent_lines:])
    intent_response = _text(
        chain.invoke(
            {
                "conversation_history": recent_history,
                "query": user_input,
                "current_date": current_date,
            }
        ).content
    )
    logger.info(f"Raw intent response: {intent_response}")
    intent_response = re.sub(r"^```json\s*|\s*```$", "", intent_response).strip()
    logger.info(f"Cleaned intent response: {intent_response}")
    intent_output = json.loads(intent_response)
    intents = intent_output.get("intents", [])
    user_queries = intent_output.get("user_queries", {})
    follow_up_message = intent_output.get("follow_up_message", "")
    logger.info(f"intents: {intents}||user_queries: {user_queries}||follow_up_message: {follow_up_message}")
    return intents, user_queries, follow_up_message


def process_user_input(prompt):
    global messages, conversation_history, llm
    messages.append({"role": "user", "content": prompt})
    conversation_history += f"\nUser: {prompt}"

    print("Analyzing your request...")
    try:
        intents, user_queries, follow_up_message = intent_agent(prompt)

        if "out_of_scope" in intents or follow_up_message:
            response = follow_up_message
            conversation_history += f"\nAssistant: {response}"
        else:
            responses = []
            routed_agents = []
            for intent in intents:
                route = resolve_route(intent)
                if route == conf.local_attraction_target:
                    chain = SmartVoyagePrompts.attraction_prompt() | llm
                    rec_response = _text(chain.invoke({"query": prompt}).content)
                    responses.append(rec_response)
                elif route:
                    agent_name = route
                    query_str = user_queries.get(intent) or prompt
                    logger.info(f"{agent_name} query: {query_str}")
                    agent = agent_network.get_agent(agent_name)
                    if agent is None:
                        responses.append(conf.msg_agent_unavailable.format(agent=agent_name))
                        continue
                    chat_history = (
                        "\n".join(conversation_history.split("\n")[-conf.history_agent_lines:-1])
                        + f"\nUser: {query_str}"
                    )
                    message = Message(content=TextContent(text=chat_history), role=MessageRole.USER)
                    task = Task(id="task-" + str(uuid.uuid4()), message=message.to_dict())
                    raw_response = asyncio.run(agent.send_task_async(task))
                    logger.info(f"{agent_name} raw response: {raw_response}")

                    if _state_value(raw_response.status.state) == "completed":
                        agent_result = raw_response.artifacts[0]["parts"][0]["text"]
                    else:
                        agent_result = _status_text(raw_response)

                    if agent_name == "WeatherQueryAssistant":
                        chain = SmartVoyagePrompts.summarize_weather_prompt() | llm
                        final_response = _text(
                            chain.invoke({"query": query_str, "raw_response": agent_result}).content
                        )
                    elif agent_name == "TicketQueryAssistant":
                        chain = SmartVoyagePrompts.summarize_ticket_prompt() | llm
                        final_response = _text(
                            chain.invoke({"query": query_str, "raw_response": agent_result}).content
                        )
                    else:
                        final_response = agent_result

                    responses.append(final_response)
                    routed_agents.append(agent_name)
                else:
                    responses.append(conf.msg_unsupported)

            response = "\n\n".join(responses)
            if routed_agents:
                logger.info(f"Routed to agents: {routed_agents}")
            conversation_history += f"\nAssistant: {response}"

        print(f"\nAssistant reply:\n{response}\n")
        messages.append({"role": "assistant", "content": response})
        return response
    except json.JSONDecodeError as json_error:
        logger.error(f"Intent JSON parsing failed: {json_error}")
        error_message = conf.msg_intent_parse_error.format(error=json_error)
        print(f"\nAssistant reply:\n{error_message}\n")
        messages.append({"role": "assistant", "content": error_message})
        return error_message
    except Exception as error:
        logger.error(f"Request failed: {error}")
        error_message = conf.msg_request_failed.format(error=error)
        print(f"\nAssistant reply:\n{error_message}\n")
        messages.append({"role": "assistant", "content": error_message})
        return error_message


def display_agent_cards():
    print("\nAgent cards:")
    for agent_name in agent_network.agents.keys():
        agent_card = agent_network.get_agent_card(agent_name)
        agent_url = agent_urls.get(agent_name, "Address not configured")
        connected = bool(agent_card and agent_card.name == agent_name)
        print(f"\n--- Agent: {agent_name} ---")
        print(f"Skills: {agent_card.skills if connected else 'Unavailable'}")
        print(f"Description: {agent_card.description if connected else 'Unavailable'}")
        print(f"Address: {agent_url}")
        print("Status: online" if connected else "Status: unavailable")


if __name__ == "__main__":
    initialize_system()
    print("SmartVoyage travel assistant")
    print("Type a question and press Enter. Type 'quit' to exit, or 'cards' to list agents.")
    display_agent_cards()

    if len(sys.argv) > 1:
        process_user_input(" ".join(sys.argv[1:]))
    else:
        while True:
            prompt = input("\nEnter your question: ").strip()
            if prompt.lower() == "quit":
                print("Thanks for using SmartVoyage.")
                break
            if prompt.lower() == "cards":
                display_agent_cards()
                continue
            if not prompt:
                continue
            process_user_input(prompt)

    print("\n---")
    print("Powered by SmartVoyage | Agent-to-agent travel assistant v2.0")
