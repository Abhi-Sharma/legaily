import os
import json
from apps.services.slre import get_structured_response
from dotenv import load_dotenv

load_dotenv()

def test_queries():
    queries = [
        "what is the punishment for cheating?",
        "what are the definitions under BNS?",
        "difference between IPC and BNS for theft",
    ]
    
    for q in queries:
        print(f"\nQuery: {q}")
        print("-" * 20)
        res = get_structured_response(q, mode="structured")
        if "error" in res:
            print(f"Error: {res['error']}")
        else:
            print(json.dumps(res["data"], indent=2))

if __name__ == "__main__":
    test_queries()
