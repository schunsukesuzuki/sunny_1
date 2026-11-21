"""Skill-owned internal sanity check ONLY, never the independent acceptance grader."""


def structural_check(dataset,output):
    if not isinstance(output,dict) or not isinstance(output.get('assignments'),list) or not isinstance(output.get('unassigned_case_ids'),list):
        raise ValueError('Missing output arrays')
    input_ids={c['case_id'] for c in dataset['cases']}
    assigned=[x['case_id'] for x in output['assignments']]
    missing=output['unassigned_case_ids']
    if len(assigned)+len(missing)!=len(input_ids) or len(set(assigned+missing))!=len(input_ids) or set(assigned+missing)!=input_ids:
        raise ValueError('Incomplete or duplicated output partition')
    return True
