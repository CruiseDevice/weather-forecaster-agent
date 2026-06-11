from src.tools.geocode import geocode
from src.tools.http import http_request

TOOLS = {
    "http_request": http_request,
    "geocode": geocode
}


TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "http_request",
            "description": "GET a URL from the NWS API (api.weather.gov), returns the JSON body.",
            "parameters": {
                "type": "object",
                "properties": {"url": {"type": "string"}},
                "required": ["url"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "geocode",
            "description": "GET a co-ordinates from the Nominatim API when a location is given in query, returns the JSON body.",
            "parameters": {
                "type": "object",
                "properties": {"city": {"type": "string"}},
                "required": ["city"],
            },
        },
    }   
]