import sys

import requests

server_url = "http://127.0.0.1:8001"


def call_order_tool(name, payload):
    response = requests.post(
        f"{server_url}/tools/{name}",
        json=payload,
        timeout=30,
    )
    response.raise_for_status()
    body = response.json()
    return body["content"][0]["text"]


def test_order_mcp():
    try:
        health = requests.get(f"{server_url}/health", timeout=5)
        health.raise_for_status()
        print("Connected to the order server. Tools can be called.")

        tools = requests.get(f"{server_url}/tools", timeout=5)
        tools.raise_for_status()
        print(f"tools-->{tools.json()}")

        # Test 1: book a train ticket.
        train_result = call_order_tool(
            "order_train",
            {
                "departure_date": "2026-10-03",
                "train_number": "ST21",
                "seat_type": "Economy",
                "number": 1,
            },
        )
        print(f"Train booking result: {train_result}")
        if train_result != "Train ticket booked successfully.":
            raise RuntimeError(f"Expected a successful train booking, got: {train_result}")

        # Test 2: book a flight ticket.
        flight_result = call_order_tool(
            "order_flight",
            {
                "departure_date": "2026-10-02",
                "flight_number": "QF401",
                "seat_type": "Economy",
                "number": 1,
            },
        )
        print(f"Flight booking result: {flight_result}")
        if flight_result != "Flight ticket booked successfully.":
            raise RuntimeError(f"Expected a successful flight booking, got: {flight_result}")

        # Test 3: book a concert ticket.
        concert_result = call_order_tool(
            "order_concert",
            {
                "start_date": "2026-10-16",
                "artist": "Tame Impala",
                "venue": "Qudos Bank Arena",
                "seat_type": "VIP",
                "number": 2,
            },
        )
        print(f"Concert booking result: {concert_result}")
        if concert_result != "Concert ticket booked successfully.":
            raise RuntimeError(f"Expected a successful concert booking, got: {concert_result}")
    except requests.RequestException as error:
        print("Start the server script first. It should be listening on http://127.0.0.1:8001")
        print(f"Order MCP test failed: {error}")
        return False
    except Exception as error:
        print(f"Order MCP test failed: {error}")
        return False
    return True


if __name__ == "__main__":
    sys.exit(0 if test_order_mcp() else 1)
