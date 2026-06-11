import sys

from src.agent import agent_run


def main() -> None:
    print(agent_run(" ".join(sys.argv[1:]) or "Forecast for Seattle"))

if __name__ == "__main__":
    main()