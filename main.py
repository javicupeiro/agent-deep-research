import sys
from pathlib import Path

# Add src directory to Python path
PROJECT_ROOT = Path(__file__).resolve().parent
SRC_PATH = PROJECT_ROOT / "src"
sys.path.append(str(SRC_PATH))

from coordinator import run_deep_research
from dotenv import load_dotenv
import argparse


def main():
    load_dotenv()

    parser = argparse.ArgumentParser(
        description="Deep research multi-agent system powered by Firecrawl"
    )
    parser.add_argument(
        "query",
        nargs="?",
        help="Research query to investigate"
    )
    args = parser.parse_args()

    user_query = args.query or input("Enter your research query: ")
    result = run_deep_research(user_query)

    with open("research_result.md", "w", encoding="utf-8") as f:
        f.write(result)

    print("Research result saved to research_result.md")


if __name__ == "__main__":
    main()
