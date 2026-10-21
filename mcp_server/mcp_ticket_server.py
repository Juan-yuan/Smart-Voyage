import json
import os
import sys
from datetime import date, datetime, timedelta
from decimal import Decimal

import pymysql
from pymysql.cursors import DictCursor
from python_a2a import FastMCP

project_directory = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_directory not in sys.path:
    sys.path.insert(0, project_directory)

from config import Config, listen_address
from create_logger import logger
from utils.format import DateEncoder, default_encoder

conf = Config()
TICKET_MCP_HOST, TICKET_MCP_PORT = listen_address(conf.ticket_mcp_url, "TICKET_MCP_URL")


class TicketService:
    def __init__(self):
        self.conn = pymysql.connect(
            host=conf.host,
            user=conf.user,
            password=conf.password,
            database=conf.database,
            charset="utf8mb4",
            cursorclass=DictCursor,
        )

    def execute_query(self, sql: str) -> str:
        try:
            self.conn.ping()
            cursor = self.conn.cursor()
            cursor.execute(sql)
            results = cursor.fetchall()
            cursor.close()
            for result in results:
                for key, value in result.items():
                    if isinstance(value, (date, datetime, timedelta, Decimal)):
                        result[key] = default_encoder(value)
            if not results:
                return json.dumps(
                    {"status": "no_data", "message": conf.mcp_ticket_no_data},
                    ensure_ascii=False,
                )
            return json.dumps({"status": "success", "data": results}, cls=DateEncoder, ensure_ascii=False)
        except Exception as error:
            logger.error(f"Ticket query failed: {error}")
            return json.dumps({"status": "error", "message": str(error)}, ensure_ascii=False)


def create_ticket_mcp_server():
    ticket_mcp = FastMCP(
        name=conf.ticket_mcp_name,
        description=conf.ticket_mcp_description,
    )

    service = TicketService()

    @ticket_mcp.tool(
        name=conf.ticket_tool_name,
        description=conf.ticket_tool_description,
    )
    def query_ticket(sql: str) -> str:
        logger.info(f"Running ticket query: {sql}")
        return service.execute_query(sql)

    try:
        ticket_mcp.run(transport="fastapi", host=TICKET_MCP_HOST, port=TICKET_MCP_PORT)
    except Exception as error:
        print(f"Server failed to start: {error}")


if __name__ == "__main__":
    service = TicketService()
    sql = "SELECT * FROM train_tickets WHERE departure_city='Sydney' LIMIT 2"
    print(service.execute_query(sql))
