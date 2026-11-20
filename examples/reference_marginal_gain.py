"""Diagnostic-only candidate for E2B tests if the LLM fails. Not model-generated.

Use the main GUI code-generation path for the intended demo; this is a known-good
candidate to help isolate Ollama errors from E2B SDK / connectivity problems.
"""
import json
import math


def solve(data):
    results = []
    for student in data["students"]:
        subjects = student["subjects"]
        alloc = {s["name"]: 0 for s in subjects}
        for _ in range(student["available_hours"]):
            eligible = [s for s in subjects if alloc[s["name"]] < s["max_hours"]]
            if not eligible:
                raise ValueError("Time budget cannot be allocated under hard limits")
            best = max(eligible, key=lambda s: (
                s["gap"] * s["priority"] * (
                    math.exp(-alloc[s["name"]] / 2.5)
                    - math.exp(-(alloc[s["name"]] + 1) / 2.5)
                ),
                s["name"],
            ))
            alloc[best["name"]] += 1
        results.append({
            "student_id": student["student_id"],
            "allocations": [{"subject": s["name"], "hours": alloc[s["name"]]} for s in subjects],
        })
    return {"plans": results}


if __name__ == "__main__":
    with open("/home/user/input.json", encoding="utf-8") as f:
        data = json.load(f)
    with open("/home/user/output.json", "w", encoding="utf-8") as f:
        json.dump(solve(data), f, ensure_ascii=False)
