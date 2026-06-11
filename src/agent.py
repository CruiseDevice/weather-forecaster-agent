import json
import sys

from src.config import MODEL, client
from src.tools import TOOL_SCHEMAS, TOOLS

SYSTEM_PROMPT = """You are a weather assistant with two tools: geocode and http_request.

Workflow:
1. If the user gives a city/place name instead of coordinates, call geocode with the place name first to get (LAT, LON).
2. GET https://api.weather.gov/points/{LAT},{LON} -> response contains properties.forecast, a URL
3. GET that URL -> properties.periods has the forecast

Rules:
- If the user already provides coordinates, skip geocoding and go straight to step 2.
- If geocoding returns multiple matches, pick the most likely one and mention which you chose.
- If geocoding fails or the place is ambiguous, ask the user to clarify instead of guessing.
- The NWS API only covers the US; if the location is outside the US, say so instead of calling the API.

Once you have all the data, return it as-is. Do not format or summarize
"""


def format_answer(user_query: str, raw_data: str) -> str:
    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": """Format the following weather data into a clear,
            human-readable answer. One line per forecast period, like: Tonight: 54°F — Partly Cloudy. Be concise.
            """},
            {"role": "user", "content": f"Question: {user_query}\n\nData:\n{raw_data}"},
        ],
    )
    return response.choices[0].message.content


def fetch_weather_data(user_query: str) -> str:
    messages = [{"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_query}]

    for _ in range(10):
        message = client.chat.completions.create(
            model=MODEL, messages=messages, tools=TOOL_SCHEMAS
        ).choices[0].message

        if not message.tool_calls:          # no tool call = final answer
            return message.content

        messages.append({"role": "assistant", "content": message.content,
                        "tool_calls": [tc.model_dump() for tc in message.tool_calls]})

        for tc in message.tool_calls:
            args = json.loads(tc.function.arguments)
            fn = TOOLS.get(tc.function.name)
            try:
                result = fn(**args) if fn else f"Error: no tool named {tc.function.name}"
            except Exception as e:
                result = f"Error: {e}" 
            print(f"[TOOL] {tc.function.name}({args}) -> {result[:200]}", file=sys.stderr) 
            messages.append({"role": "tool", "tool_call_id": tc.id, "content": result})

    return "Run out of iterations"


def agent_run(user_query: str) -> str:
    raw_data = fetch_weather_data(user_query)
    formatted = format_answer(user_query, raw_data)
    return formatted