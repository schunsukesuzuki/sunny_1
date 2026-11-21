"""v0.13 deterministic presales decision support.

The rubric uses ONLY locally persisted synthetic experiment records. It never
converts an evidence ID, LLM opinion, or a synthetic metric into customer proof.
No LLM is invoked; the criteria and next actions are fixed and auditable.
"""
from __future__ import annotations

from typing import Any

RUBRIC_VERSION = "PRESALES-ASSESSMENT-v0.13.0"
SYNTHETIC = "SUPPORTED_SYNTHETIC"
CONTROL = "DEMO_CONTROLLED"
HOLD = "HOLD"
UNKNOWN = "UNVERIFIED"


def _criterion(key: str, title: str, status: str, finding: str,
               refs: list[str], next_action: str) -> dict[str, Any]:
    return {"id": key, "title": title, "status": status, "finding": finding,
            "evidence_refs": refs, "next_action": next_action}


def _metrics(rows: Any) -> dict[str, Any] | None:
    if not isinstance(rows, list) or not rows or not all(isinstance(row, dict) and row.get("valid") is True for row in rows):
        return None
    for row in rows:
        for key in ("assigned_hours", "missed_deadlines"):
            value = row.get(key)
            if not isinstance(value, (int, float)) or isinstance(value, bool) or value < 0:
                return None
    return {"missed": sum(row["missed_deadlines"] for row in rows),
            "worked_hours": sum(row["assigned_hours"] for row in rows),
            "seed_count": len(rows),
            "by_seed": {row.get("seed"): {"missed": row["missed_deadlines"],
                           "worked_hours": row["assigned_hours"]} for row in rows}}


def assess(exp: dict, run: dict, prop: dict, approval: dict, *, code_integrity: bool = False) -> dict:
    """Return a conservative, deterministic two-axis rubric (no external claims)."""
    held = exp.get("holdout") or {}
    fifo = _metrics(held.get("fifo"))
    generated = _metrics(held.get("generated"))
    deadline = _metrics(held.get("deadline"))
    aligned = bool(fifo and generated and len(fifo["by_seed"]) == fifo["seed_count"]
                   and fifo["by_seed"].keys() == generated["by_seed"].keys()
                   and len(generated["by_seed"]) == generated["seed_count"])
    improved = bool(aligned and all(
        generated["by_seed"][s]["worked_hours"] == f["worked_hours"]
        and generated["by_seed"][s]["missed"] <= f["missed"]
        for s, f in fifo["by_seed"].items())
        and any(generated["by_seed"][s]["missed"] < f["missed"]
                for s, f in fifo["by_seed"].items()))
    technical = bool(improved and exp.get("holdout_executed") is True
                     and exp.get("r1_independent_kpi_improvement_pass") is True
                     and run.get("implementation_validity") == "PASS" and code_integrity)
    proper_approval = approval.get("decision") == "approved" and prop.get("condition") == "counterexample"
    diagnostic_qwen = prop.get("diagnosis_matches_rubric") is True
    diagnostic_oda = prop.get("finance_diagnosis_matches_rubric") is True
    diagnostics_ok = diagnostic_qwen and diagnostic_oda
    human_override = approval.get("domain_review_override") is True
    holdout_sandbox = bool(held.get("generated") and all(row.get("sandbox_id") for row in held["generated"]))
    code_selected = bool(exp.get("selected_code_sha256") and code_integrity)
    dev_holdout = bool(exp.get("dev_seeds") and exp.get("holdout_seeds")
                       and set(exp["dev_seeds"]).isdisjoint(set(exp["holdout_seeds"])))
    # This is a LOCAL audit pointer, not an independent real-world evidence source.
    register = [
        {"id": "E01", "source": f"runs/{run['run_id']}/run.json", "provenance": "SYNTHETIC",
         "description": "R0 contract, E2B execution and synthetic DEV/HOLDOUT metrics",
         "validity": "Local experiment result; not customer-reported"},
        {"id": "E02", "source": f"proposals/{prop['proposal_id']}/proposal.json", "provenance": "SYNTHETIC",
         "description": "Mock requirement counterexample, Qwen/ODA diagnostics and rubric status",
         "validity": "Synthetic fixture; evidence IDs are application-defined"},
        {"id": "E03", "source": f"approvals/{approval['approval_id']}/approval.json", "provenance": "DEMO_CONTROLLED",
         "description": "Demo human decision / original HOLD retained if overridden",
         "validity": "Simulated approval, not actual client authorization"},
        {"id": "E04", "source": f"experiments/{exp['experiment_id']}/experiment.json", "provenance": "SYNTHETIC",
         "description": "Generated code evaluation, held-out results, constraints, attempts",
         "validity": "Synthetic E2B-based test; not production deployment"},
        {"id": "E05", "source": "No external/customer evidence attached", "provenance": "UNVERIFIED",
         "description": "Customer demand, actual productivity, costs, legal and operating constraints",
         "validity": "No independent external verification"},
    ]
    value = [
        _criterion("BV-01", "顧客課題と業務KPIの整合（合成ケース）", SYNTHETIC if technical else HOLD,
                   "固定稼働でFIFOより期限超過が減ることを合成HOLDOUTで確認" if technical else
                   "同一条件のR1独立KPI改善が確認できない", ["E01", "E04"],
                   "顧客の実データでSLA・処理時間・案件到着分布を検証する"),
        _criterion("BV-02", "代替案の定量比較", SYNTHETIC if technical and deadline and deadline["by_seed"].keys() == fifo["by_seed"].keys() and deadline["seed_count"] == fifo["seed_count"] else HOLD,
                   "FIFO・期限優先の固定ヒューリスティック・生成R1を同条件で比較" if technical and deadline and deadline["by_seed"].keys() == fifo["by_seed"].keys() and deadline["seed_count"] == fifo["seed_count"] else
                   "比較対象または有効なHOLDOUT評価が不足している", ["E01", "E04"],
                   "顧客が承認した基準・失敗コストで代替案を再比較する"),
        _criterion("BV-03", "MVPの範囲と承認ゲート", CONTROL if proper_approval else HOLD,
                   "変更要件と人間のデモ承認が記録され、検証対象は担当者割当ロジックに限定" if proper_approval else
                   "承認チェーンが不足", ["E02", "E03"],
                   "顧客とスコープ、除外事項、受入基準を合意する"),
        _criterion("BV-04", "実顧客の需要・支払意思", UNKNOWN,
                   "顧客インタビュー、受注、価格受容の外部証拠なし", ["E05"],
                   "顧客ヒアリングと有償PoCの支払意思を確認する"),
        _criterion("BV-05", "収益性・投資回収", UNKNOWN,
                   "開発費・運用費・CAC・料金・期限超過削減の金銭価値は未実測", ["E05"],
                   "提案原価・運用負荷・回収可能額を見積もる"),
    ]
    delivery = [
        _criterion("AI-01", "生成コードの隔離実行・制約検証", SYNTHETIC if technical and holdout_sandbox else HOLD,
                   "E2B実行結果と独立評価器で資格・容量・処理を評価" if technical and holdout_sandbox else
                   "有効なE2B実行・制約評価の証跡が不足", ["E04"],
                   "権限、ネットワーク出口、CPU/メモリ制限を含む実環境のセキュリティ審査を行う"),
        _criterion("AI-02", "DEVとHOLDOUTの分離・再現性", SYNTHETIC if technical and dev_holdout and code_selected else HOLD,
                   "異なるseedでDEV/非開示HOLDOUTを分離しコードハッシュを記録" if technical and dev_holdout and code_selected else
                   "独立HOLDOUT・コード選択の証跡が不足", ["E04"],
                   "seed追加・顧客分布の変動・回帰テストで頑健性を測る"),
        _criterion("AI-03", "LLM要件診断の品質", CONTROL if diagnostics_ok else HOLD,
                   "両診断が現行の固定ルーブリックを満たす。ただし意味的正しさは未保証" if diagnostics_ok else
                   "少なくとも一方が独立ルーブリックでHOLD。承認履歴でHOLDは解消されない", ["E02"],
                   "多ケース・複数回の独立診断ベンチマークと誤判定分析を実施する"),
        _criterion("AI-04", "人間の関与と監査可能性", CONTROL if proper_approval else HOLD,
                   ("モデル診断HOLDを保持したままデモ上の人間審査で技術検証を継続" if human_override else
                    "人間のデモ承認と要件改訂の追跡が可能") if proper_approval else
                   "人間のデモ承認が確認できない", ["E02", "E03", "E04"],
                   "顧客側の権限分掌・承認者・監査保持期間を設計する"),
        _criterion("AI-05", "業務ワークフロー・本番運用", UNKNOWN,
                   "顧客基盤への統合、認証、SLA、障害対応、監視・復旧は未検証", ["E05"],
                   "API・監査運用・例外処理・データ移行の設計レビューを行う"),
        _criterion("AI-06", "法務・個人情報・規制", UNKNOWN,
                   "実顧客のデータ処理、GDPR、保険規制との適合を検証していない", ["E05"],
                   "適用法令、データ保護、委託契約、保険金判断の人間関与を専門家と確認する"),
    ]
    verdict = "CUSTOMER_DISCOVERY_ONLY" if technical and proper_approval else "HOLD_TECHNICAL"
    explanation = ("合成HOLDOUTの技術結果は有望。ただし事業価値と本番提供は未検証。"
                   "人間の技術審査を前提とした顧客ディスカバリーへの移行のみ検討可能。"
                   if verdict == "CUSTOMER_DISCOVERY_ONLY" else
                   "独立技術評価または改訂承認の根拠が不足。顧客提案の前に技術HOLDを解消する。")
    return {"rubric_version": RUBRIC_VERSION, "experiment_id": exp["experiment_id"],
            "scope": "SYNTHETIC_DEMONSTRATION_ONLY", "real_customer_validity": UNKNOWN,
            "source_register": register,
            "summary_metrics": {"fifo": fifo, "generated": generated, "deadline_heuristic": deadline,
                                "fixed_hours_and_deadline_improvement": technical,
                                "diagnosis_qwen_rubric_pass": diagnostic_qwen,
                                "diagnosis_oda_rubric_pass": diagnostic_oda,
                                "human_override": human_override,
                                "holdout_executed": bool(exp.get("holdout_executed")),
                                "selected_code_integrity": code_integrity},
            "axes": [{"id": "BUSINESS", "title": "Business Value & Feasibility", "criteria": value},
                     {"id": "DELIVERY", "title": "AI Delivery & Operational Readiness", "criteria": delivery}],
            "decision": {"code": verdict, "description": explanation,
                         "status": "GO" if verdict == "CUSTOMER_DISCOVERY_ONLY" else "HOLD",
                         "stage": "CUSTOMER_DISCOVERY" if verdict == "CUSTOMER_DISCOVERY_ONLY" else "TECHNICAL_VALIDATION",
                         "production_status": "NO_GO",
                         "production_go": False, "customer_business_go": False,
                         "automatic_diagnosis_accepted": diagnostics_ok},
            "next_actions": [{"priority": "P1", "action": "顧客の業務SLA・分布・処理時間・資格・例外を実測で確認", "owner_role": "Customer / product owner"},
                             {"priority": "P1", "action": "モデル診断HOLDの誤判定を再現し、独立レビューを継続", "owner_role": "AI technical reviewer"},
                             {"priority": "P2", "action": "実顧客ROI、PoC費用、採算、支払意思を検証", "owner_role": "Business development"},
                             {"priority": "P2", "action": "本番ワークフロー、認証、監査・規制・データ保護を精査", "owner_role": "Delivery / compliance"}],
            "disclaimer": "Evidence ID correctness != evidence validity != diagnostic correctness. "
                          "SIM-SLA-001 and report E01-E05 are local/synthetic references, not external citations. "
                          "No customer, market, legal, regulatory or production approval is inferred."}


def markdown(record: dict) -> str:
    """Markdown generated from the stored deterministic report, not LLM prose."""
    def cell(v: Any) -> str:
        return str(v).replace("|", "\\|").replace("\n", " ").replace("\r", " ")

    d = record["decision"]
    m = record["summary_metrics"]
    lines = ["# Project Feasibility Assessment — v0.13", "",
             "> 合成・架空顧客に限定した技術プリセールス用の判断支援。実顧客・市場・法令・本番運用の適合を保証しません。", "",
             f"- Assessment ID: `{record['assessment_id']}`",
             f"- Experiment ID: `{record['experiment_id']}`",
             f"- Generated at (UTC): {record['created_at']}",
             f"- Rubric: `{record['rubric_version']}`",
             f"- Provisional decision: **{d['status']}** — stage `{d['stage']}` ({d['code']})",
             f"- Production decision: **{d['production_status']}** (production GO: **NO**)",
             f"- Rationale: {d['description']}", "",
             "## 技術実験の要約", "",
             "| 合成HOLDOUT | FIFO | 生成R1 | 期限優先参照（ヒューリスティック） |",
             "|---|---:|---:|---:|"]
    for key, label in (("missed", "期限超過件数"), ("worked_hours", "実働時間（時間）")):
        values = [m.get(k, {}).get(key, "—") if isinstance(m.get(k), dict) else "—" for k in ("fifo", "generated", "deadline_heuristic")]
        lines.append("| " + label + " | " + " | ".join(map(cell, values)) + " |")
    lines += ["", "- 参照方式は数学的な最適解ではありません。HOLDOUTの合成結果を実業務効果へ外挿できません。",
              f"- 要件診断ルーブリック Qwen: **{'PASS' if m['diagnosis_qwen_rubric_pass'] else 'HOLD'}** / ODA: **{'PASS' if m['diagnosis_oda_rubric_pass'] else 'HOLD'}**",
              f"- 人間のデモ上書き承認: **{'YES' if m['human_override'] else 'NO'}**。上書き承認は元の診断HOLDをPASSに変更しません。", ""]
    for axis in record["axes"]:
        lines += [f"## {axis['title']}", "", "| 評価項目 | 状態 | 根拠 | 次の検証 |", "|---|---|---|---|"]
        for c in axis["criteria"]:
            lines.append("| " + " | ".join(map(cell, [c['id'] + " " + c['title'], c['status'], c['finding'] + " [" + ", ".join(c['evidence_refs']) + "]", c['next_action']])) + " |")
        lines.append("")
    lines += ["## Evidence register — 根拠の出所", "",
              "| ID | 証拠種類 | ローカル出所 | 限界 |", "|---|---|---|---|"]
    for e in record["source_register"]:
        lines.append("| " + " | ".join(map(cell, [e["id"], e["provenance"], e["source"], e["validity"]])) + " |")
    lines += ["", "証拠IDの正確性 ≠ 証拠の妥当性 ≠ 診断の正しさ。",
              "**合成の証拠IDは実在する顧客資料・一次資料ではありません。**", "",
              "## Next validation actions", ""]
    for step in record["next_actions"]:
        lines.append(f"- **{step['priority']} / {step['owner_role']}**: {step['action']}")
    lines += ["", "## Audit metadata", "",
              "- Local source snapshot SHA256 values (data integrity pointers, not signed attestations):", ""]
    for k, h in record["source_sha256"].items():
        lines.append(f"  - `{k}`: `{h}`")
    lines += ["", record["disclaimer"], ""]
    return "\n".join(lines)
