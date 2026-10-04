import asyncio
import html
import json
import os
import re
import sys
import uuid
from datetime import datetime
from zoneinfo import ZoneInfo

import streamlit as st
from langchain_openai import ChatOpenAI
from python_a2a import A2AClient, AgentNetwork, Message, MessageRole, Task, TextContent

project_directory = os.path.dirname(os.path.abspath(__file__))
if project_directory not in sys.path:
    sys.path.insert(0, project_directory)

from config import Config
from create_logger import logger
from main import _require_setting, _state_value, _status_text, _text
from main_prompts import SmartVoyagePrompts

conf = Config()

css_path = os.path.join(project_directory, "css", "app.css")
with open(css_path, encoding="utf-8") as css_file:
    st.markdown(f"<style>{css_file.read()}</style>", unsafe_allow_html=True)

if "messages" not in st.session_state:
    st.session_state.messages = []
if "agent_network" not in st.session_state:
    st.session_state.agent_urls = {
        "WeatherQueryAssistant": _require_setting("WEATHER_AGENT_URL", conf.weather_agent_url),
        "TicketQueryAssistant": _require_setting("TICKET_AGENT_URL", conf.ticket_agent_url),
        "TicketOrderAssistant": _require_setting("ORDER_AGENT_URL", conf.order_agent_url),
    }
    network = AgentNetwork(name="Travel Assistant Network")
    for name, url in st.session_state.agent_urls.items():
        network.add(name, A2AClient(url, timeout=120))
    st.session_state.agent_network = network
    st.session_state.llm = ChatOpenAI(
        model=conf.model_name,
        api_key=conf.api_key,
        base_url=conf.base_url,
        temperature=0.1,
    )
    st.session_state.conversation_history = ""


def intent_agent(user_input):
    chain = SmartVoyagePrompts.intent_prompt() | st.session_state.llm
    current_date = datetime.now(ZoneInfo("Australia/Sydney")).strftime("%Y-%m-%d")
    recent_history = "\n".join(st.session_state.conversation_history.split("\n")[-6:])
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


AGENT_LABELS = {
    "WeatherQueryAssistant": "Weather",
    "TicketQueryAssistant": "Tickets",
    "TicketOrderAssistant": "Booking",
}

SUGGESTIONS = [
    ("Weather", "What is the weather in Sydney on 2026-09-28?"),
    ("Tickets", "Find an Economy train from Sydney to Melbourne on 2026-10-03."),
    ("Places", "Recommend outdoor places to visit in Sydney."),
]

typed = st.chat_input("Ask for a forecast, a ticket, a booking, or a place")
prompt = typed

lead = '<p class="sv-lead">Check the weather, compare fares, and reserve a seat.</p>'
st.markdown(
    f"""
    <header class="sv-top">
        <h1>SmartVoyage</h1>
    </header>
    {lead}
    """,
    unsafe_allow_html=True,
)

with st.container(key="stage", height=480, autoscroll=True):
    if st.session_state.messages and st.button("New conversation", type="tertiary", key="reset-chat"):
        st.session_state.messages = []
        st.session_state.conversation_history = ""
        st.rerun()

    if st.session_state.messages:
        for message in st.session_state.messages:
            avatar = ":material/person:" if message["role"] == "user" else ":material/explore:"
            with st.chat_message(message["role"], avatar=avatar):
                source = message.get("source")
                if message["role"] == "assistant" and source:
                    st.markdown(f'<p class="sv-source">{html.escape(source)}</p>', unsafe_allow_html=True)
                st.markdown(message["content"])
    else:
        for index, (label, suggestion) in enumerate(SUGGESTIONS):
            st.markdown(f'<p class="sv-prompt-kicker">{html.escape(label)}</p>', unsafe_allow_html=True)
            if st.button(suggestion, key=f"suggestion-{index}", type="secondary"):
                prompt = suggestion

    if prompt:
        with st.chat_message("user", avatar=":material/person:"):
            st.markdown(prompt)
        st.session_state.messages.append({"role": "user", "content": prompt})
        st.session_state.conversation_history += f"\nUser: {prompt}"

        llm = st.session_state.llm
        with st.spinner("Checking with SmartVoyage..."):
            try:
                intents, user_queries, follow_up_message = intent_agent(prompt)
                sources = []

                if "out_of_scope" in intents or follow_up_message:
                    response = follow_up_message or (
                        "I can help with weather, train and flight tickets, concert seats, bookings, and places to visit."
                    )
                    sources.append("SmartVoyage")
                    st.session_state.conversation_history += f"\nAssistant: {response}"
                else:
                    responses = []
                    routed_agents = []
                    for intent in intents:
                        logger.info(f"Handling intent: {intent}")
                        if intent == "weather":
                            agent_name = "WeatherQueryAssistant"
                        elif intent in ["flight", "train", "concert"]:
                            agent_name = "TicketQueryAssistant"
                        elif intent == "order":
                            agent_name = "TicketOrderAssistant"
                        else:
                            agent_name = None

                        if intent == "attraction":
                            chain = SmartVoyagePrompts.attraction_prompt() | llm
                            rec_response = _text(chain.invoke({"query": prompt}).content)
                            responses.append(rec_response)
                            sources.append("Places")
                        elif agent_name:
                            query_str = user_queries.get(intent) or prompt
                            logger.info(f"{agent_name} query: {query_str}")
                            agent = st.session_state.agent_network.get_agent(agent_name)
                            label = AGENT_LABELS.get(agent_name, agent_name)
                            if agent is None:
                                responses.append(f"{label} is unavailable right now. Please try again in a moment.")
                                sources.append(label)
                                continue
                            chat_history = (
                                "\n".join(st.session_state.conversation_history.split("\n")[-7:-1])
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
                            sources.append(label)
                        else:
                            responses.append(
                                "I can help with weather, train and flight tickets, concert seats, bookings, and places to visit."
                            )
                            sources.append("SmartVoyage")

                    response = "\n\n".join(responses)
                    if routed_agents:
                        logger.info(f"Routed to agents: {routed_agents}")
                    st.session_state.conversation_history += f"\nAssistant: {response}"

                st.session_state.messages.append(
                    {"role": "assistant", "content": response, "source": " · ".join(dict.fromkeys(sources))}
                )
            except json.JSONDecodeError as json_error:
                logger.error(f"Intent JSON parsing failed: {json_error}")
                st.session_state.messages.append(
                    {
                        "role": "assistant",
                        "content": "I could not read that request. Name a city, a date, and what you need.",
                        "source": "SmartVoyage",
                    }
                )
            except Exception as error:
                logger.error(f"Request failed: {error}")
                st.session_state.messages.append(
                    {
                        "role": "assistant",
                        "content": "SmartVoyage could not complete that request. Please try again in a moment.",
                        "source": "SmartVoyage",
                    }
                )
            st.rerun()
