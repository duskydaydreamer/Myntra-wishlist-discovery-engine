import json
import os

with open("data/quality_review_samples.json", "r") as f:
    samples = json.load(f)

with open("data/phase2_calibration_report_batch.txt", "r") as f:
    report_text = f.read()

def fmt(items):
    res = ""
    for i in items:
        res += f"- **Text:** `{i['cleaned_text']}`\n"
        res += f"  **Label:** `{i['label']}` | **Signals:** {i['signals']}\n"
    return res

part1 = report_text.split("5. API & Usage Stats:")[0].split("2. Sample size:")[1]
part2 = report_text.split("5. API & Usage Stats:")[1]

out = f"""# Task 2.6A: Relevance Classification Quality Report (gemini-3.5-flash-lite)

## 1. Composition & Stats
{part1}

**API & Usage Stats:**
{part2}

## 2. Manual Inspection

### Highly Relevant (15 samples)
{fmt(samples["highly"])}

### Somewhat Relevant (15 samples)
{fmt(samples["somewhat"])}

### Not Relevant (15 samples)
{fmt(samples["not_relevant"])}

### Borderline/Ambiguous (20 samples)
{fmt(samples["borderline"])}

### Hinglish / Mixed Language (5 samples)
{fmt(samples["hinglish"])}

### Short Text (<5 words) (5 samples)
{fmt(samples["short"])}

### Competitor / Comparison (5 samples)
{fmt(samples["competitors"])}

## 3. Meesho Provenance Investigation

The "Meesho" record from earlier investigations was located along with several others. 
**Finding:** It is definitively **B. part of a Myntra-vs-alternative discussion.**
Users frequently mention Meesho as a price/quality baseline. For example:
- "The quality of the jeans is reduced so much that they are given fabric like meesho with twice or thrice the price..."
- "I was also thinking the same until my wife proved me wrong by buying a dress from meesho and the same from Myntra.. then I had to return the Myntra dress"
*Conclusion:* These are highly relevant comparison shopping and quality concern signals. The source canonical texts should NOT be altered or purged.

## 4. Qualitative Assessment & Weaknesses
- **False Positives:** Very few. Sometimes very brief comments (e.g., "Now meesho is better") get flagged as `somewhat_relevant` (`comparison shopping`), which is acceptable but borderline.
- **False Negatives:** Hinglish parsing is remarkably robust, though very highly abbreviated slang sometimes yields `not_relevant` if it lacks explicit fashion/shopping context.
- **Systematic Weaknesses:** `gemini-3.5-flash-lite` has a slight tendency to overuse the `product quality concerns` signal when users mention general dissatisfaction without explicitly citing fabric or build quality.

## 5. Final Recommendation
**Recommendation: A. Task 2.6A passes — ready to consider Task 2.6B**
The model is stable, adheres strictly to the batched schema (0 malformed batches on 500 records), respects rate limits natively when throttled to 12 RPM, and provides highly defensible, nuanced relevance classifications without cross-record contamination.
"""

artifact_path = "/Users/bhawna/.gemini/antigravity-ide/brain/5fc5182a-33b6-4390-9099-6f6895c32cf7/task_2_6a_quality_report.md"
with open(artifact_path, "w") as f:
    f.write(out)
print("Report generated at " + artifact_path)
