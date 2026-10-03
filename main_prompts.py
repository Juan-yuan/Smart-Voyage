import os
import sys

from langchain_core.prompts import ChatPromptTemplate

project_directory = os.path.dirname(os.path.abspath(__file__))
if project_directory not in sys.path:
    sys.path.insert(0, project_directory)

from config import Config

conf = Config()


def _prompt_template(name, value):
    if not value or not str(value).strip():
        raise RuntimeError(f"Missing {name}. Add it to the .env file.")
    return ChatPromptTemplate.from_template(value)


class SmartVoyagePrompts:
    @staticmethod
    def intent_prompt():
        return _prompt_template("INTENT_PROMPT", conf.intent_prompt)

    @staticmethod
    def summarize_weather_prompt():
        return _prompt_template("SUMMARIZE_WEATHER_PROMPT", conf.summarize_weather_prompt)

    @staticmethod
    def summarize_ticket_prompt():
        return _prompt_template("SUMMARIZE_TICKET_PROMPT", conf.summarize_ticket_prompt)

    @staticmethod
    def attraction_prompt():
        return _prompt_template("ATTRACTION_PROMPT", conf.attraction_prompt)


if __name__ == "__main__":
    samples = [
        (
            SmartVoyagePrompts.intent_prompt(),
            {
                "current_date": "2026-10-03",
                "conversation_history": "user: I am traveling from Sydney.",
                "query": "What is the weather today?",
            },
        ),
        (
            SmartVoyagePrompts.summarize_weather_prompt(),
            {
                "query": "What is the weather in Sydney on 2026-10-02?",
                "raw_response": "Sydney 2026-10-02: Partly cloudy, 15-23C, humidity 68%.",
            },
        ),
        (
            SmartVoyagePrompts.summarize_ticket_prompt(),
            {
                "query": "Train from Sydney to Melbourne on 2026-10-03, Economy",
                "raw_response": "Sydney to Melbourne 2026-10-03 07:40:00: train ST21, Economy, price 141.0 AUD, 46 seats left",
            },
        ),
        (
            SmartVoyagePrompts.attraction_prompt(),
            {"query": "Recommend outdoor attractions in Sydney."},
        ),
    ]
    for prompt, values in samples:
        messages = prompt.format_messages(**values)
        if not str(messages[0].content).strip():
            raise SystemExit("A prompt formatted to an empty message.")
    print("Prompt templates formatted successfully.")
