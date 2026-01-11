import sys
from pathlib import Path

# Add src directory to Python path
PROJECT_ROOT = Path(__file__).resolve().parent
SRC_PATH = PROJECT_ROOT / "src"
sys.path.append(str(SRC_PATH))

from coordinator import run_deep_research
from dotenv import load_dotenv


def main():
    load_dotenv()

    user_query = input("Enter your research query: ")
    result = run_deep_research(user_query)

    with open("research_result.md", "w", encoding="utf-8") as f:
        f.write(result)

    print("Research result saved to research_result.md")


if __name__ == "__main__":
    main()
