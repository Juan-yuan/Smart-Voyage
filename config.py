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
    """Read a double-quoted value that may span lines. Inner quotes are escaped as \\\"."""
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
    """Return the host and port from a service URL stored in .env."""
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


def service_origin(url, setting_name):
    """Return scheme://host:port for a service URL stored in .env."""
    host, port = listen_address(url, setting_name)
    parsed = urlparse(str(url).strip())
    if not parsed.scheme:
        raise RuntimeError(f"{setting_name} must include a scheme, host, and port.")
    return f"{parsed.scheme}://{host}:{port}"


_load_env_files()

project_root = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')


# Configuration
class Config:
    def __init__(self):
        self.OPENAI_API_KEY = _require_env('OPENAI_API_KEY', 'openai_api_key', 'API_KEY', 'api_key')
        self.OPENAI_BASE_URL = _require_env('OPENAI_BASE_URL', 'BASE_URL')
        self.LLM_MODEL = _require_env('LLM_MODEL', 'MODEL_NAME')
        self.api_key = self.OPENAI_API_KEY
        self.base_url = self.OPENAI_BASE_URL
        self.model_name = self.LLM_MODEL

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

        self.weather_sql_prompt = _first_env('WEATHER_SQL_PROMPT')
        self.weather_mcp_url = _first_env('WEATHER_MCP_URL')
        self.weather_agent_url = _first_env('WEATHER_AGENT_URL')
        self.ticket_mcp_url = _first_env('TICKET_MCP_URL')
        self.ticket_query_url = _first_env('TICKET_QUERY_URL')
        self.ticket_agent_url = _first_env('TICKET_AGENT_URL')
        self.ticket_sql_prompt = _first_env('TICKET_SQL_PROMPT')
        self.ticket_summary_prompt = _first_env('TICKET_SUMMARY_PROMPT')
        self.order_mcp_url = _first_env('ORDER_MCP_URL')
        self.order_agent_url = _first_env('ORDER_AGENT_URL')
        self.order_system_prompt = _first_env('ORDER_SYSTEM_PROMPT')
        self.intent_prompt = _first_env('INTENT_PROMPT')
        self.summarize_weather_prompt = _first_env('SUMMARIZE_WEATHER_PROMPT')
        self.summarize_ticket_prompt = _first_env('SUMMARIZE_TICKET_PROMPT')
        self.attraction_prompt = _first_env('ATTRACTION_PROMPT')
        self.weather_test_summary_prompt = _first_env('WEATHER_TEST_SUMMARY_PROMPT')

    def call_dashscope(self, prompt):
        """Call the LLM and stream the generated answer, same as Insurance-RAG-Assistant."""
        try:
            completion = self.client.chat.completions.create(
                model=self.LLM_MODEL,
                messages=[
                    {"role": "system", "content": "You are a helpful assistant."},
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
