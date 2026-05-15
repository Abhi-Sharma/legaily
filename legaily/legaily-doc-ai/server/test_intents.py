import sys
import os

from apps.services.slre import get_structured_response

queries = [
    "Order 39 Rule 1 CPC injunction",
    "Section 302 IPC punishment",
    "What is the doctrine of basic structure?"
]

for q in queries:
    print("\n" + "="*60 + "\nQUERY: " + q + "\n" + "="*60)
    res = get_structured_response(q)
    print(res.get("data", res)[:500] + "\n...[truncated]")
