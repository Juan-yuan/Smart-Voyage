import json
import sys

import requests

server_url = "http://127.0.0.1:8002"


def call_query_weather(sql):
    response = requests.post(
        f"{server_url}/tools/query_weather",
        json={"sql": sql},
        timeout=30,
    )
    response.raise_for_status()
    payload = response.json()
    text = payload["content"][0]["text"]
    return json.loads(text)


def test_weather_mcp():
    try:
        health = requests.get(f"{server_url}/health", timeout=5)
        health.raise_for_status()
        print("Connected to the weather server. Tools can be called.")

        tools = requests.get(f"{server_url}/tools", timeout=5)
        tools.raise_for_status()
        print(f"tools-->{tools.json()}")

        # Test 1: query weather for a specific date.
        sql = "SELECT * FROM weather_data WHERE city = 'Sydney' AND fx_date = '2026-09-28'"
        result_data = call_query_weather(sql)
        print(f"Weather result for the selected date: {result_data}")
        if result_data.get("status") != "success" or not result_data.get("data"):
            raise RuntimeError(f"Expected Sydney weather for 2026-09-28, got: {result_data}")

        sql_range = (
            "SELECT * FROM weather_data WHERE city = 'Sydney' "
            "AND fx_date BETWEEN '2026-09-28' AND '2026-09-30'"
        )
        result_range_data = call_query_weather(sql_range)
        print(f"Weather result for the date range: {result_range_data}")
        if result_range_data.get("status") != "success" or len(result_range_data.get("data", [])) < 3:
            raise RuntimeError(f"Expected three Sydney forecast days, got: {result_range_data}")
    except requests.RequestException as error:
        print("Start the server script first. It should be listening on http://127.0.0.1:8002")
        print(f"Weather MCP test failed: {error}")
        return False
    except Exception as error:
        print(f"Weather MCP test failed: {error}")
        return False
    return True


if __name__ == "__main__":
    sys.exit(0 if test_weather_mcp() else 1)
