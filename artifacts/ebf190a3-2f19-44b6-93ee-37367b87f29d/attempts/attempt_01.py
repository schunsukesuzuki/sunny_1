import json
import math

def allocate_hours(student, available_hours):
    # 各科目の初期割当を0とする
    allocations = [{'subject': subject['name'], 'hours': 0} for subject in student['subjects']]
    
    # 各科目のgapとpriorityからwを計算
    subjects_with_w = []
    for subject in student['subjects']:
        w = subject['gap'] * subject['priority']
        subjects_with_w.append({
            'name': subject['name'],
            'max_hours': subject['max_hours'],
            'w': w,
            'current_hours': 0
        })
    
    # 残り時間
    remaining_hours = available_hours
    
    # marginal gainを計算して割当
    while remaining_hours > 0:
        best_subject = None
        best_marginal_gain = -1
        
        for subject in subjects_with_w:
            if subject['current_hours'] < subject['max_hours']:
                # marginal utility delta = w*(exp(-h/2.5)-exp(-(h+1)/2.5))
                h = subject['current_hours']
                marginal_gain = subject['w'] * (math.exp(-h / 2.5) - math.exp(-(h + 1) / 2.5))
                
                if marginal_gain > best_marginal_gain:
                    best_marginal_gain = marginal_gain
                    best_subject = subject
        
        if best_subject is None:
            break
        
        best_subject['current_hours'] += 1
        remaining_hours -= 1
    
    # 割当結果を返す
    result_allocations = []
    for subject in subjects_with_w:
        result_allocations.append({
            'subject': subject['name'],
            'hours': subject['current_hours']
        })
    
    return result_allocations


def main():
    with open('/home/user/input.json', 'r') as f:
        data = json.load(f)
    
    plans = []
    for student in data['students']:
        allocations = allocate_hours(student, student['available_hours'])
        plans.append({
            'student_id': student['student_id'],
            'allocations': allocations
        })
    
    output_data = {'plans': plans}
    
    with open('/home/user/output.json', 'w') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)


if __name__ == '__main__':
    main()