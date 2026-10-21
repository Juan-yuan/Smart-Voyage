import os
import sys

from python_a2a import FastMCP

project_directory = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_directory not in sys.path:
    sys.path.insert(0, project_directory)

from config import Config, listen_address
from create_logger import logger

conf = Config()
ORDER_MCP_HOST, ORDER_MCP_PORT = listen_address(conf.order_mcp_url, "ORDER_MCP_URL")


def create_order_mcp_server():
    order_mcp = FastMCP(
        name=conf.order_mcp_name,
        description=conf.order_mcp_description,
    )

    @order_mcp.tool(
        name=conf.order_train_tool_name,
        description=conf.order_train_tool_description,
    )
    def order_train(departure_date: str, train_number: str, seat_type: str, number: int) -> str:
        logger.info(f"Booking train ticket: {departure_date}, {train_number}, {seat_type}, {number}")
        logger.info(conf.order_train_success)
        return conf.order_train_success

    @order_mcp.tool(
        name=conf.order_flight_tool_name,
        description=conf.order_flight_tool_description,
    )
    def order_flight(departure_date: str, flight_number: str, seat_type: str, number: int) -> str:
        logger.info(f"Booking flight ticket: {departure_date}, {flight_number}, {seat_type}, {number}")
        logger.info(conf.order_flight_success)
        return conf.order_flight_success

    @order_mcp.tool(
        name=conf.order_concert_tool_name,
        description=conf.order_concert_tool_description,
    )
    def order_concert(start_date: str, artist: str, venue: str, seat_type: str, number: int) -> str:
        return conf.order_concert_success

    try:
        order_mcp.run(transport="fastapi", host=ORDER_MCP_HOST, port=ORDER_MCP_PORT)
    except Exception as error:
        print(f"Server failed to start: {error}")


if __name__ == "__main__":
    create_order_mcp_server()
