import json

f1 = json.load(open("data/phase3a_eval_results.json"))
f2 = json.load(open("data/phase3a_remaining_results.json"))

def count_valid(data):
    return sum(1 for item in data if item.get("extracted") and isinstance(item["extracted"], dict) and item["extracted"].get("evidence_quote") and item["extracted"].get("evidence_quote") != "?")

print(f"eval_results valid: {count_valid(f1)}")
print(f"remaining valid: {count_valid(f2)}")
