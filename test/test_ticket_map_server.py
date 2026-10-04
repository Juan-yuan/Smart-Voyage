import json
import os
import sys

import requests

project_directory = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_directory not in sys.path:
    sys.path.insert(0, project_directory)

from config import Config, service_origin

server_url = service_origin(Config().ticket_mcp_url, "TICKET_MCP_URL")


def call_query_ticket(sql):
    response = requests.post(
        f"{server_url}/tools/query_ticket",
        json={"sql": sql},
        timeout=30,
    )
    response.raise_for_status()
    payload = response.json()
    text = payload["content"][0]["text"]
    return json.loads(text)


def test_ticket_mcp():
    try:
        health = requests.get(f"{server_url}/health", timeout=5)
        health.raise_for_status()
        print("Connected to the ticket server. Tools can be called.")

        tools = requests.get(f"{server_url}/tools", timeout=5)
        tools.raise_for_status()
        print(f"tools-->{tools.json()}")

        sql_flights = (
            "SELECT * FROM flight_tickets WHERE departure_city = 'Sydney' "
            "AND arrival_city = 'Melbourne' AND DATE(departure_time) = '2026-10-02' "
            "AND cabin_type = 'Economy'"
        )
        result_flights = call_query_ticket(sql_flights)
        print(f"Flight query result: {result_flights}")
        if result_flights.get("status") != "success" or not result_flights.get("data"):
            raise RuntimeError(f"Expected a Sydney to Melbourne economy flight, got: {result_flights}")

        sql_trains = (
            "SELECT * FROM train_tickets WHERE departure_city = 'Sydney' "
            "AND arrival_city = 'Melbourne' AND DATE(departure_time) = '2026-10-03' "
            "AND seat_type = 'Economy'"
        )
        result_trains = call_query_ticket(sql_trains)
        print(f"Train query result: {result_trains}")
        if result_trains.get("status") != "success" or not result_trains.get("data"):
            raise RuntimeError(f"Expected a Sydney to Melbourne economy train, got: {result_trains}")

        sql_concerts = (
            "SELECT * FROM concert_tickets WHERE city = 'Sydney' "
            "AND artist = 'Tame Impala' AND DATE(start_time) = '2026-10-16' "
            "AND ticket_type = 'VIP'"
        )
        result_concerts = call_query_ticket(sql_concerts)
        print(f"Concert ticket query result: {result_concerts}")
        if result_concerts.get("status") != "success" or not result_concerts.get("data"):
            raise RuntimeError(f"Expected a Tame Impala VIP ticket, got: {result_concerts}")
    except requests.RequestException as error:
        print("Start the ticket MCP server from TICKET_MCP_URL first.")
        print(f"Ticket MCP test failed: {error}")
        return False
    except Exception as error:
        print(f"Ticket MCP test failed: {error}")
        return False
    return True


if __name__ == "__main__":
    sys.exit(0 if test_ticket_mcp() else 1)
