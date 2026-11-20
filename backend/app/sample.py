"""Entirely synthetic data: educational proxy, not actual learning outcomes."""
from __future__ import annotations

import random
from .models import ProjectInput

SUBJECTS = ("数学", "英語", "国語", "理科")

SAMPLE_PROJECT = {
    "title": "教育SaaS：AI個別学習プランニング（架空案件）",
    "brief": (
        "当社は全国の学習塾に学習管理システム（LMS）を提供しています。"
        "新しい有料オプションとして、生徒の学習可能時間、科目別の理解度、"
        "試験までの優先度を考慮して、週次学習計画を自動生成するサービスを検討しています。"
        "講師が手動で学習計画を作る時間を減らしながら、生徒の制約を厳守したいです。"
        "LLMが本当に必要なのか、ルールベースと最適化も比較して検討してください。"
        "まずはプロトタイプによる技術的成立性の検証と、料金仮説の整理をお願いします。"
    ),
    "business": {
        "monthly_price_yen": 12000,
        "paying_schools": 30,
        "monthly_operating_cost_yen": 180000,
        "hours_saved_per_school": 5,
        "teacher_hourly_cost_yen": 2500,
    },
    "seed": 42,
    "evaluation_seeds": 3,
    "holdout_seeds": 2,
    "students_count": 12,
    "min_quality_ratio": 0.98,
    "min_improvement_ratio": 1.01,
    "max_repair_attempts": 2,
}


def create_dataset(project: ProjectInput) -> dict:
    rng = random.Random(project.seed)
    students = []
    for i in range(project.students_count):
        subjects = [
            {
                "name": name,
                "gap": round(rng.uniform(0.2, 0.95), 2),
                "priority": rng.randint(1, 5),
                "max_hours": rng.randint(4, 7),
            }
            for name in SUBJECTS
        ]
        students.append({
            "student_id": f"S{i + 1:03d}",
            "available_hours": rng.randint(7, 13),
            "subjects": subjects,
        })
    return {
        "schema_version": "1.0",
        "project_type": "weekly_study_plan",
        "units": {"hours": "integer hours per week", "gap": "synthetic [0,1]"},
        "students": students,
    }
