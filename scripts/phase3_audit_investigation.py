import json

files = ["data/phase3a_eval_results.json", "data/phase3a_remaining_results.json", "data/phase3a_eval_results_v2.json"]
for f in files:
    try:
        data = json.load(open(f))
        print(f"{f}: {len(data)} items")
    except Exception as e:
        print(f"{f}: error {e}")
