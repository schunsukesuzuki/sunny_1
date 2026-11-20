import json
import math

def calculate_utility(gap, priority, hours):
    # 極大化される効用関数: w*(1-exp(-hours/2.5)), w=gap*priority
    w = gap * priority
    return w * (1 - math.exp(-hours / 2.5))

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
                # 現在の時間での効用
                current_utility = calculate_utility(subject['w']/subject['w'], 1, subject['current_hours'])
                # 時間を1増やしたときの効用
                new_utility = calculate_utility(subject['w']/subject['w'], 1, subject['current_hours'] + 1)
                marginal_gain = new_utility - current_utility
                
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