import logging
import os

from openai import OpenAI

logger = logging.getLogger(__name__)


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
            for line in env_file:
                line = line.strip()
                if not line or line.startswith('#') or '=' not in line:
                    continue
                key, _, value = line.partition('=')
                key = key.strip()
                value = value.strip().strip('"').strip("'")
                if key and not os.environ.get(key):
                    os.environ[key] = value
    lowercase_key = os.environ.get('api_key', '').strip() or os.environ.get('openai_api_key', '').strip()
    if lowercase_key and not os.environ.get('API_KEY'):
        os.environ['API_KEY'] = lowercase_key
    if lowercase_key and not os.environ.get('OPENAI_API_KEY'):
        os.environ['OPENAI_API_KEY'] = lowercase_key


def _first_env(*names, default=''):
    for name in names:
        value = os.getenv(name)
        if value:
            return value
    return default


_load_env_files()

project_root = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')


# Configuration
class Config:
    def __init__(self):
        self.OPENAI_API_KEY = _first_env('OPENAI_API_KEY', 'openai_api_key', 'API_KEY', 'api_key')
        self.OPENAI_BASE_URL = _first_env(
            'OPENAI_BASE_URL',
            'BASE_URL',
            default='https://api.openai.com/v1',
        )
        self.LLM_MODEL = _first_env('LLM_MODEL', 'MODEL_NAME', default='gpt-5-mini')
        self.api_key = self.OPENAI_API_KEY
        self.base_url = self.OPENAI_BASE_URL
        self.model_name = self.LLM_MODEL

        try:
            self.client = OpenAI(api_key=self.OPENAI_API_KEY, base_url=self.OPENAI_BASE_URL)
        except Exception as e:
            logger.error(f"Failed to initialize the OpenAI client: {e}")
            raise

        # Database configuration
        self.host = _first_env('MYSQL_HOST', default='localhost')
        self.user = _first_env('MYSQL_USER', default='root')
        self.password = _first_env('MYSQL_PASSWORD', default='mysql123')
        self.database = _first_env('MYSQL_DATABASE', default='travel_rag')

        self.log_file = _first_env(
            'LOG_FILE',
            default=os.path.join(project_root, 'SmartVoyage', 'logs/app.log'),
        )

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
            logger.error(f"LLM call failed: {e}")
            return f"Error: LLM call failed - {e}"


config = Config()


if __name__ == '__main__':
    print(config.OPENAI_BASE_URL)
    print(config.LLM_MODEL)
    print(config.log_file)
