import json
import math


def solve_student(student):
    subjects = student["subjects"]
    target = student["available_hours"]
    # DP maps consumed hours to (proxy utility numerator, allocation tuple).
    states = {0: (0.0, ())}
    for subject in subjects:
        weight = subject["gap"] * subject["priority"]
        next_states = {}
        for total, (value, allocations) in states.items():
            for hours in range(subject["max_hours"] + 1):
                new_total = total + hours
                if new_total > target:
                    continue
                candidate = (
                    value + weight * (1.0 - math.exp(-hours / 2.5)),
                    allocations + (hours,),
                )
                previous = next_states.get(new_total)
                if previous is None or candidate[0] > previous[0] + 1e-12:
                    next_states[new_total] = candidate
        states = next_states
    if target not in states:
        raise ValueError("No feasible allocation")
    return [
        {"subject": s["name"], "hours": h}
        for s, h in zip(subjects, states[target][1])
    ]


def solve(data):
    return {"plans": [
        {"student_id": s["student_id"], "allocations": solve_student(s)}
        for s in data["students"]
    ]}


if __name__ == "__main__":
    with open("/home/user/input.json", encoding="utf-8") as f:
        data = json.load(f)
    with open("/home/user/output.json", "w", encoding="utf-8") as f:
        json.dump(solve(data), f, ensure_ascii=False)
