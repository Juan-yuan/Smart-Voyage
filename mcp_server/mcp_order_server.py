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
        name="OrderTools",
        description="Ticket booking tools for train tickets, flight tickets, and concert tickets.",
    )

    @order_mcp.tool(
        name="order_train",
        description="Book a train ticket by departure date, train number, seat type, and quantity.",
    )
    def order_train(departure_date: str, train_number: str, seat_type: str, number: int) -> str:
        """
        Args:
            departure_date: Departure date, for example '2026-10-03'
            train_number: Train number, for example 'ST21'
            seat_type: Seat type, for example 'Economy'
            number: Number of tickets to book
        """
        logger.info(f"Booking train ticket: {departure_date}, {train_number}, {seat_type}, {number}")
        logger.info("Train ticket booked successfully.")
        return "Train ticket booked successfully."

    @order_mcp.tool(
        name="order_flight",
        description="Book a flight ticket by departure date, flight number, seat type, and quantity.",
    )
    def order_flight(departure_date: str, flight_number: str, seat_type: str, number: int) -> str:
        """
        Args:
            departure_date: Departure date, for example '2026-10-02'
            flight_number: Flight number, for example 'QF401'
            seat_type: Seat type, for example 'Economy'
            number: Number of tickets to book
        """
        logger.info(f"Booking flight ticket: {departure_date}, {flight_number}, {seat_type}, {number}")
        logger.info("Flight ticket booked successfully.")
        return "Flight ticket booked successfully."

    @order_mcp.tool(
        name="order_concert",
        description="Book a concert ticket by start date, artist, venue, seat type, and quantity.",
    )
    def order_concert(start_date: str, artist: str, venue: str, seat_type: str, number: int) -> str:
        """
        Args:
            start_date: Start date, for example '2026-10-16'
            artist: Artist name, for example 'Tame Impala'
            venue: Venue, for example 'Qudos Bank Arena'
            seat_type: Seat type, for example 'VIP'
            number: Number of tickets to book
        """
        return "Concert ticket booked successfully."


    try:
        order_mcp.run(transport="fastapi", host=ORDER_MCP_HOST, port=ORDER_MCP_PORT)
    except Exception as error:
        print(f"Server failed to start: {error}")


if __name__ == "__main__":
    create_order_mcp_server()
