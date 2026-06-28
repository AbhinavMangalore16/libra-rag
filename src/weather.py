import os
from mcp.server.fastmcp import FastMCP
from dotenv import load_dotenv
import requests
load_dotenv()
mcp = FastMCP("weather")

@mcp.tool()
def get_weather(location: str)-> str:
    """Get the current weather for a given location"""
    API_KEY = os.getenv("WEATHER_API_KEY")
    url = f"http://api.weatherapi.com/v1/current.json?key={API_KEY}&q={location}"
    response = requests.get(url).json()
    if "error" in response:
        return f"Could not find weather for {location}"
    temp = response["current"]["temp_c"]
    cond = response["current"]["condition"]["text"]
    return f"The weather in {location} is currently {temp}°C with {cond}."

if __name__ == "__main__":
    print("Starting MCP weather-service server...")
    mcp.run(
        transport="streamable-http",
    )
