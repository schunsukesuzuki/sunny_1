"""Reproducible E2B standalone script constructed from reviewed skill sources.

The code is identical to the local functions. No evaluator rules or secrets enter
this bundle; all independent validation stays in backend/app/domain.py.
"""
from pathlib import Path
from .schemas import SKILL_VERSION, STRATEGIES

COMPONENTS=('schemas','priority','feasibility','scarcity','optimizer','validators','runner')

def source_files() -> dict[str, str]:
    root=Path(__file__).resolve().parent
    return {f'{part}.py':(root/f'{part}.py').read_text(encoding='utf-8') for part in COMPONENTS}

def sandbox_source(strategy: str) -> str:
    if strategy not in STRATEGIES:
        raise ValueError('Unknown or unsupported skill strategy')
    # Each reviewed module is a self-contained set of Python functions. Only the
    # imports and definitions above are included; no arbitrary LLM source.
    text='"""PINNED Domain Skill; not an LLM-generated candidate."""\nimport json\n'
    for fname,content in source_files().items():
        text+=f'\n# --- {fname} ---\n'+'\n'.join(line for line in content.splitlines() if not line.startswith('from .'))+'\n'
    text+='\nif __name__ == "__main__":\n'
    text+='    with open("/home/user/input.json", encoding="utf-8") as f: dataset=json.load(f)\n'
    text+=f'    output=schedule(dataset, strategy={strategy!r})\n'
    text+='    with open("/home/user/output.json", "w", encoding="utf-8") as f: json.dump(output,f,ensure_ascii=False)\n'
    return text

def manifest() -> dict:
    import hashlib
    files=source_files()
    return {'skill_id':'claims_allocation','version':SKILL_VERSION,
            'strategies':list(STRATEGIES),'components':{k:hashlib.sha256(v.encode()).hexdigest() for k,v in files.items()},
            'scope':'Synthetic claims reviewer scheduling, NOT actual adjudication',
            'independent_evaluator':'backend/app/domain.py:validate',
            'solver_claim':'bounded_beam is bounded heuristic, not exact optimizer',
            'security':'No unapproved LLM code can be substituted for a skill component'}
