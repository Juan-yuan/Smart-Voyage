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

from config import Config
from create_logger import logger
from utils.format import DateEncoder, default_encoder

conf = Config()


class WeatherService:
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
                    {"status": "no_data", "message": "No weather data found. Check the city and date."},
                    ensure_ascii=False,
                )
            return json.dumps({"status": "success", "data": results}, cls=DateEncoder, ensure_ascii=False)
        except Exception as error:
            logger.error(f"Weather query failed: {error}")
            return json.dumps({"status": "error", "message": str(error)}, ensure_ascii=False)


def create_weather_mcp_server():
    weather_mcp = FastMCP(
        name="WeatherTools",
        description="Weather query tool based on the weather_data table.",
    )

    service = WeatherService()

    @weather_mcp.tool(
        name="query_weather",
        description=(
            'Query weather data. Pass a SQL statement, for example '
            'SELECT * FROM weather_data WHERE city = "Sydney" AND fx_date = "2026-09-28"'
        ),
    )
    def query_weather(sql: str) -> str:
        logger.info(f"Running weather query: {sql}")
        return service.execute_query(sql)

    try:
        # python_a2a FastMCP serves tools over HTTP with the fastapi transport.
        weather_mcp.run(transport="fastapi", host="127.0.0.1", port=8002)
    except Exception as error:
        print(f"Server failed to start: {error}")


if __name__ == "__main__":
    service = WeatherService()
    sql = "SELECT * FROM weather_data WHERE city='Sydney' LIMIT 2"
    print(service.execute_query(sql))
