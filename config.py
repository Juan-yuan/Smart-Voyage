import json
import logging
import os
from urllib.parse import urlparse

from openai import OpenAI

logger = logging.getLogger(__name__)


def _unescape_double_quoted(text):
    decoded = []
    index = 0
    while index < len(text):
        if text[index] == '\\' and index + 1 < len(text):
            escaped = text[index + 1]
            decoded.append({
                'n': '\n',
                'r': '\r',
                't': '\t',
                '"': '"',
                '\\': '\\',
            }.get(escaped, escaped))
            index += 2
            continue
        decoded.append(text[index])
        index += 1
    return ''.join(decoded)


def _read_double_quoted(value, lines, index):
    raw = value[1:]
    while True:
        cursor = 0
        while cursor < len(raw):
            if raw[cursor] == '\\':
                cursor += 2
                continue
            if raw[cursor] == '"':
                return _unescape_double_quoted(raw[:cursor]), index
            cursor += 1
        index += 1
        if index >= len(lines):
            raise ValueError('Unterminated double-quoted value in .env')
        raw += '\n' + lines[index].rstrip('\n').rstrip('\r')


def _parse_env_lines(lines):
    parsed = {}
    index = 0
    while index < len(lines):
        stripped = lines[index].strip()
        if not stripped or stripped.startswith('#') or '=' not in stripped:
            index += 1
            continue
        key, _, value = stripped.partition('=')
        key = key.strip()
        value = value.strip()
        if value.startswith('"'):
            value, index = _read_double_quoted(value, lines, index)
        elif len(value) >= 2 and value[0] == value[-1] and value[0] == "'":
            value = value[1:-1]
        if key and key not in parsed:
            parsed[key] = value
        index += 1
    return parsed


def _load_env_files():
    here = os.path.dirname(os.path.abspath(__file__))
    candidates = [
        os.path.abspath(os.path.join(here, '.env')),
        os.path.abspath(os.path.join(here, '..', '.env')),
    ]
    for path in candidates:
        if not os.path.isfile(path):
            continue
        with open(path, encoding='utf-8') as env_file:
            for key, value in _parse_env_lines(env_file.readlines()).items():
                if key and not os.environ.get(key):
                    os.environ[key] = value
    lowercase_key = os.environ.get('api_key', '').strip() or os.environ.get('openai_api_key', '').strip()
    if lowercase_key and not os.environ.get('API_KEY'):
        os.environ['API_KEY'] = lowercase_key
    if lowercase_key and not os.environ.get('OPENAI_API_KEY'):
        os.environ['OPENAI_API_KEY'] = lowercase_key


def listen_address(url, setting_name):
    if not url or not str(url).strip():
        raise RuntimeError(f"Missing {setting_name}. Add it to the .env file.")
    parsed = urlparse(str(url).strip())
    if not parsed.hostname or parsed.port is None:
        raise RuntimeError(f"{setting_name} must include a host and port.")
    return parsed.hostname, parsed.port


def _first_env(*names, default=''):
    for name in names:
        value = os.getenv(name)
        if value:
            return value
    return default


def _require_env(*names):
    value = _first_env(*names)
    if not value or not str(value).strip():
        raise RuntimeError(f"Missing {names[0]}. Add it to the .env file.")
    return value


def _require_int(name):
    return int(_require_env(name))


def _require_float(name):
    return float(_require_env(name))


def _require_json(name):
    return json.loads(_require_env(name))


def service_origin(url, setting_name):
    host, port = listen_address(url, setting_name)
    parsed = urlparse(str(url).strip())
    if not parsed.scheme:
        raise RuntimeError(f"{setting_name} must include a scheme, host, and port.")
    return f"{parsed.scheme}://{host}:{port}"


_load_env_files()

project_root = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')


class Config:
    def __init__(self):
        self.OPENAI_API_KEY = _require_env('OPENAI_API_KEY', 'openai_api_key', 'API_KEY', 'api_key')
        self.OPENAI_BASE_URL = _require_env('OPENAI_BASE_URL', 'BASE_URL')
        self.LLM_MODEL = _require_env('LLM_MODEL', 'MODEL_NAME')
        self.api_key = self.OPENAI_API_KEY
        self.base_url = self.OPENAI_BASE_URL
        self.model_name = self.LLM_MODEL
        self.llm_system_prompt = _require_env('LLM_SYSTEM_PROMPT')
        self.llm_temperature = _require_float('LLM_TEMPERATURE')
        self.app_timezone = _require_env('APP_TIMEZONE')
        self.history_intent_lines = _require_int('HISTORY_INTENT_LINES')
        self.history_agent_lines = _require_int('HISTORY_AGENT_LINES')
        self.agent_timeout_seconds = _require_int('AGENT_TIMEOUT_SECONDS')
        self.network_name = _require_env('NETWORK_NAME')

        try:
            self.client = OpenAI(api_key=self.OPENAI_API_KEY, base_url=self.OPENAI_BASE_URL)
        except Exception as e:
            logger.error(f"Failed to initialize the OpenAI client: {e}")
            raise

        self.host = _require_env('MYSQL_HOST')
        self.user = _require_env('MYSQL_USER')
        self.password = _require_env('MYSQL_PASSWORD')
        self.database = _require_env('MYSQL_DATABASE')

        self.log_file = _first_env(
            'LOG_FILE',
            default=os.path.join(project_root, 'SmartVoyage', 'logs/app.log'),
        )

        self.weather_sql_prompt = _require_env('WEATHER_SQL_PROMPT')
        self.weather_mcp_url = _require_env('WEATHER_MCP_URL')
        self.weather_agent_url = _require_env('WEATHER_AGENT_URL')
        self.ticket_mcp_url = _require_env('TICKET_MCP_URL')
        self.ticket_query_url = _require_env('TICKET_QUERY_URL')
        self.ticket_agent_url = _require_env('TICKET_AGENT_URL')
        self.ticket_sql_prompt = _require_env('TICKET_SQL_PROMPT')
        self.ticket_summary_prompt = _require_env('TICKET_SUMMARY_PROMPT')
        self.order_mcp_url = _require_env('ORDER_MCP_URL')
        self.order_agent_url = _require_env('ORDER_AGENT_URL')
        self.order_system_prompt = _require_env('ORDER_SYSTEM_PROMPT')
        self.intent_prompt = _require_env('INTENT_PROMPT')
        self.summarize_weather_prompt = _require_env('SUMMARIZE_WEATHER_PROMPT')
        self.summarize_ticket_prompt = _require_env('SUMMARIZE_TICKET_PROMPT')
        self.attraction_prompt = _require_env('ATTRACTION_PROMPT')
        self.weather_test_summary_prompt = _require_env('WEATHER_TEST_SUMMARY_PROMPT')

        self.weather_schema_sql = _require_env('WEATHER_SCHEMA_SQL')
        self.ticket_schema_sql = _require_env('TICKET_SCHEMA_SQL')
        self.weather_row_template = _require_env('WEATHER_ROW_TEMPLATE')
        self.train_row_template = _require_env('TRAIN_ROW_TEMPLATE')
        self.flight_row_template = _require_env('FLIGHT_ROW_TEMPLATE')
        self.concert_row_template = _require_env('CONCERT_ROW_TEMPLATE')

        self.intent_agent_map = _require_json('INTENT_AGENT_MAP')
        self.agent_labels = _require_json('AGENT_LABELS')
        self.ui_suggestions = _require_json('UI_SUGGESTIONS')
        self.ui_lead = _require_env('UI_LEAD')
        self.ui_chat_placeholder = _require_env('UI_CHAT_PLACEHOLDER')
        self.ui_spinner_text = _require_env('UI_SPINNER_TEXT')

        self.msg_out_of_scope = _require_env('MSG_OUT_OF_SCOPE')
        self.msg_unsupported = _require_env('MSG_UNSUPPORTED')
        self.msg_weather_need_city_date = _require_env('MSG_WEATHER_NEED_CITY_DATE')
        self.msg_ticket_need_details = _require_env('MSG_TICKET_NEED_DETAILS')
        self.msg_ticket_need_basic = _require_env('MSG_TICKET_NEED_BASIC')
        self.msg_weather_ask_select = _require_env('MSG_WEATHER_ASK_SELECT')
        self.msg_ticket_ask_select = _require_env('MSG_TICKET_ASK_SELECT')
        self.msg_weather_no_data = _require_env('MSG_WEATHER_NO_DATA')
        self.msg_ticket_no_data = _require_env('MSG_TICKET_NO_DATA')
        self.msg_weather_failed = _require_env('MSG_WEATHER_FAILED')
        self.msg_ticket_failed = _require_env('MSG_TICKET_FAILED')
        self.msg_booking_failed = _require_env('MSG_BOOKING_FAILED')
        self.msg_booking_missing = _require_env('MSG_BOOKING_MISSING')
        self.msg_booking_unknown_tool = _require_env('MSG_BOOKING_UNKNOWN_TOOL')
        self.msg_booking_none = _require_env('MSG_BOOKING_NONE')
        self.msg_service_unavailable = _require_env('MSG_SERVICE_UNAVAILABLE')
        self.msg_agent_unavailable = _require_env('MSG_AGENT_UNAVAILABLE')
        self.msg_agent_unavailable_ui = _require_env('MSG_AGENT_UNAVAILABLE_UI')
        self.msg_intent_parse_error = _require_env('MSG_INTENT_PARSE_ERROR')
        self.msg_intent_parse_error_ui = _require_env('MSG_INTENT_PARSE_ERROR_UI')
        self.msg_request_failed = _require_env('MSG_REQUEST_FAILED')
        self.msg_request_failed_ui = _require_env('MSG_REQUEST_FAILED_UI')
        self.mcp_weather_no_data = _require_env('MCP_WEATHER_NO_DATA')
        self.mcp_ticket_no_data = _require_env('MCP_TICKET_NO_DATA')

        self.weather_agent_card = _require_json('WEATHER_AGENT_CARD')
        self.ticket_agent_card = _require_json('TICKET_AGENT_CARD')
        self.order_agent_card = _require_json('ORDER_AGENT_CARD')

        self.weather_mcp_name = _require_env('WEATHER_MCP_NAME')
        self.weather_mcp_description = _require_env('WEATHER_MCP_DESCRIPTION')
        self.weather_tool_name = _require_env('WEATHER_TOOL_NAME')
        self.weather_tool_description = _require_env('WEATHER_TOOL_DESCRIPTION')
        self.ticket_mcp_name = _require_env('TICKET_MCP_NAME')
        self.ticket_mcp_description = _require_env('TICKET_MCP_DESCRIPTION')
        self.ticket_tool_name = _require_env('TICKET_TOOL_NAME')
        self.ticket_tool_description = _require_env('TICKET_TOOL_DESCRIPTION')
        self.order_mcp_name = _require_env('ORDER_MCP_NAME')
        self.order_mcp_description = _require_env('ORDER_MCP_DESCRIPTION')
        self.order_train_tool_name = _require_env('ORDER_TRAIN_TOOL_NAME')
        self.order_train_tool_description = _require_env('ORDER_TRAIN_TOOL_DESCRIPTION')
        self.order_flight_tool_name = _require_env('ORDER_FLIGHT_TOOL_NAME')
        self.order_flight_tool_description = _require_env('ORDER_FLIGHT_TOOL_DESCRIPTION')
        self.order_concert_tool_name = _require_env('ORDER_CONCERT_TOOL_NAME')
        self.order_concert_tool_description = _require_env('ORDER_CONCERT_TOOL_DESCRIPTION')
        self.order_train_success = _require_env('ORDER_TRAIN_SUCCESS')
        self.order_flight_success = _require_env('ORDER_FLIGHT_SUCCESS')
        self.order_concert_success = _require_env('ORDER_CONCERT_SUCCESS')

        self.local_attraction_target = 'LOCAL_ATTRACTION'

    def call_dashscope(self, prompt):
        try:
            completion = self.client.chat.completions.create(
                model=self.LLM_MODEL,
                messages=[
                    {"role": "system", "content": self.llm_system_prompt},
                    {"role": "user", "content": prompt},
                ],
                timeout=30,
                stream=True,
            )
            for chunk in completion:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        except Exception as e:
            return f"Error: LLM call failed - {e}"


config = Config()


if __name__ == '__main__':
    print('Configuration loaded.')
