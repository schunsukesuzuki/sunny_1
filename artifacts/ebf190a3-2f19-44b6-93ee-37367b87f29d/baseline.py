import json


def solve(data):
    plans = []
    for student in data["students"]:
        remaining = student["available_hours"]
        ordered = sorted(student["subjects"], key=lambda s: (s["gap"] * s["priority"], s["name"]), reverse=True)
        allocations = {s["name"]: 0 for s in student["subjects"]}
        for s in ordered:
            hours = min(remaining, s["max_hours"])
            allocations[s["name"]] = hours
            remaining -= hours
        plans.append({"student_id": student["student_id"], "allocations": [
            {"subject": s["name"], "hours": allocations[s["name"]]}
            for s in student["subjects"]
        ]})
    return {"plans": plans}


if __name__ == "__main__":
    with open("/home/user/input.json", encoding="utf-8") as f:
        data = json.load(f)
    result = solve(data)
    with open("/home/user/output.json", "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False)
