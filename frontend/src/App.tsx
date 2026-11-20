import { useEffect, useState } from 'react'
import type { CandidateResult, GeneratedCode, Health, ProjectInput, RequirementsDraft, RunResult, PlanComparison, ServiceDesign, CustomerEvidence, RequirementRefinementProposal } from './types'

const SAMPLE: ProjectInput = {
  title: '教育SaaS：AI個別学習プランニング（架空案件）',
  brief: '当社は全国の学習塾に学習管理システム（LMS）を提供しています。新しい有料オプションとして、生徒の学習可能時間、科目別の理解度、試験までの優先度を考慮して、週次学習計画を自動生成するサービスを検討しています。講師が手動で学習計画を作る時間を減らしながら、生徒の制約を厳守したいです。LLMが本当に必要なのか、ルールベースと最適化も比較して検討してください。まずはプロトタイプによる技術的成立性の検証と、料金仮説の整理をお願いします。',
  business: { monthly_price_yen: 12000, paying_schools: 30, monthly_operating_cost_yen: 180000, hours_saved_per_school: 5, teacher_hourly_cost_yen: 2500 },
  seed: 42, evaluation_seeds: 3, holdout_seeds: 2, students_count: 12, min_quality_ratio: 0.98, min_improvement_ratio: 1.01, max_repair_attempts: 2
}

const yen = (value: number) => `¥${value.toLocaleString('ja-JP')}`
const format = (value: number | null, digits = 5) => value === null ? 'N/A' : value.toFixed(digits)

async function request<T>(url: string, body?: unknown): Promise<T> {
  const response = await fetch(url, body === undefined ? {} : {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body)
  })
  if (!response.ok) {
    let message = `HTTP ${response.status}`
    try {
      const data = await response.json() as { detail?: unknown }
      if (data.detail) message = typeof data.detail === 'string' ? data.detail : JSON.stringify(data.detail)
    } catch { /* keep HTTP error */ }
    throw new Error(message)
  }
  return response.json() as Promise<T>
}

function Step({ value, done }: { value: number; done: boolean }) {
  return <span className={`step-number ${done ? 'step-done' : ''}`}>{done ? '✓' : value}</span>
}
function ListEdit({ label, values, onChange }: { label: string; values: string[]; onChange: (x: string[]) => void }) {
  return <label className="field"><span>{label}</span>
    <textarea rows={3} className="compact-textarea" value={values.join('\n')}
      onChange={event => onChange(event.target.value.split('\n').filter(Boolean))}/>
  </label>
}
function CandidateCard({ title, data }: { title: string; data: CandidateResult }) {
  return <div className="candidate-card">
    <div className="candidate-header"><strong>{title}</strong><span className={`state ${data.hard_constraint_pass ? 'ok' : 'warn'}`}>
      {data.hard_constraint_pass ? 'ALL SEEDS PASS' : 'FAILED'}</span></div>
    <small>{data.algorithm}</small>
    <div className="candidate-score">{format(data.score)} <small>平均代理効用</small></div>
    <div className="candidate-stats"><span>合格 {data.passed_seeds}/{data.total_seeds} seeds</span><span>σ={format(data.score_std)}</span></div>
    <div className="candidate-stats"><span>最低 {format(data.min_score)}</span><span>平均実行 {data.elapsed_seconds.toFixed(3)}s</span></div>
    {data.violations.length > 0 && <div className="violations">{data.violations.slice(0, 4).map((v, i) => <div key={i}>{v}</div>)}</div>}
    {data.sample_plans.length > 0 && <details><summary>生成された計画の例</summary><pre>{JSON.stringify(data.sample_plans, null, 2)}</pre></details>}
    <details><summary>E2B証跡（seed別）</summary><pre>{data.per_seed.map(e => `seed ${e.seed}: ${e.status}, score=${e.score ?? 'N/A'}, sandbox=${e.sandbox_id}, output_sha256=${e.output_sha256 ?? 'N/A'}\n${e.stderr}`).join('\n')}</pre><code className="hash">Source SHA256: {data.source_sha256}</code></details>
  </div>
}

function PlanCard({ plan, datasetLabel }: { plan: PlanComparison; datasetLabel: string }) {
  const renderValue = (v: number | null) => v === null ? 'N/A' : `${v}h`
  return <article className="plan-card">
    <div className="plan-title"><b>{plan.student_id}</b><span>週 {plan.available_hours} 時間 / {datasetLabel} seed {plan.seed}</span></div>
    <table className="plan-table"><thead><tr><th>科目 / 条件</th><th>静的Greedy</th><th>厳密DP</th><th>Qwen生成</th></tr></thead><tbody>
      {plan.subjects.map(s => <tr key={s.subject}>
        <th>{s.subject}<small>gap {s.gap.toFixed(2)} · priority {s.priority} · 上限{s.max_hours}h</small></th>
        {([['baseline', s.baseline_hours], ['optimal', s.optimal_hours], ['generated', s.generated_hours]] as const).map(([kind, h]) =>
          <td key={kind}><span className="plan-hours">{renderValue(h)}</span><div className="plan-track"><span className={`plan-bar ${kind}`} style={{width: `${h === null ? 0 : h / Math.max(s.max_hours, 1) * 100}%`}}/></div></td>
        )}
      </tr>)}
    </tbody></table>
    {!plan.generated_valid && <p className="violations">Qwen候補はこの生徒の有効な配分を確認できませんでした。</p>}
  </article>
}

export default function App() {
  const [project, setProject] = useState<ProjectInput>(SAMPLE)
  const [health, setHealth] = useState<Health | null>(null)
  const [healthError, setHealthError] = useState(false)
  const [requirements, setRequirements] = useState<RequirementsDraft | null>(null)
  const [design, setDesign] = useState<ServiceDesign | null>(null)
  const [evidence, setEvidence] = useState<CustomerEvidence[]>([])
  const [evidenceDraft, setEvidenceDraft] = useState<Omit<CustomerEvidence,'evidence_id'>>({
    requirement_id: 'AC-01', provenance: 'synthetic', verdict: 'inconclusive',
    observation: '', source_reference: '', human_verified: false, reviewer: ''
  })
  const [revision, setRevision] = useState(0)
  const [parentRunId, setParentRunId] = useState<string | null>(null)
  const [proposal, setProposal] = useState<RequirementRefinementProposal | null>(null)
  const [generated, setGenerated] = useState<GeneratedCode | null>(null)
  const [code, setCode] = useState('')
  const [result, setResult] = useState<RunResult | null>(null)
  const [busy, setBusy] = useState<'analyze' | 'design' | 'generate' | 'run' | 'refine' | ''>('')
  const [error, setError] = useState('')

  const refresh = () => void request<Health>('/api/health').then(v => { setHealth(v); setHealthError(false) })
    .catch(() => { setHealth(null); setHealthError(true) })
  useEffect(() => { refresh() }, [])

  const updateProject = (patch: Partial<ProjectInput>) => {
    setProject(prev => ({ ...prev, ...patch })); setRequirements(null); setDesign(null); setGenerated(null); setCode(''); setResult(null)
  }
  const updateBusiness = (key: keyof ProjectInput['business'], value: number) => {
    setProject(prev => ({ ...prev, business: { ...prev.business, [key]: value } })); setResult(null)
  }
  const updateRequirement = (key: keyof RequirementsDraft, value: string | string[]) => {
    if (!requirements) return
    if (key === 'acceptance_criteria') setEvidence([])
    setRequirements({ ...requirements, [key]: value }); setDesign(null); setGenerated(null); setCode(''); setResult(null)
  }
  async function act<T>(phase: typeof busy, fn: () => Promise<T>, done: (value: T) => void) {
    setBusy(phase); setError('')
    try { done(await fn()) } catch (e) { setError(e instanceof Error ? e.message : String(e)) }
    finally { setBusy('') }
  }
  const analyze = () => void act('analyze', () => request<RequirementsDraft>('/api/analyze', { project }), value => {
    setRequirements(value); setDesign(null); setGenerated(null); setCode(''); setResult(null)
  })
  const designService = () => {
    if (!requirements) return
    void act('design', () => request<ServiceDesign>('/api/design', { project, requirements }), value => {
      setDesign(value); setGenerated(null); setCode(''); setResult(null)
    })
  }
  const updateDesign = (key: keyof ServiceDesign, value: string | string[]) => {
    if (!design) return
    setDesign({ ...design, [key]: value, design_source: 'human_edited_unapproved' }); setGenerated(null); setCode(''); setResult(null)
  }
  const addEvidence = () => {
    if (!evidenceDraft.observation.trim()) return
    const newId = Math.max(0, ...evidence.map(e=>Number(e.evidence_id.replace('EV-','')) || 0)) + 1
    const item = { ...evidenceDraft, evidence_id: `EV-${String(newId).padStart(2,'0')}` }
    setEvidence(prev => [...prev, item]); setResult(null)
    setEvidenceDraft(prev => ({ ...prev, observation: '', source_reference: '', human_verified: false }))
  }
  const generate = () => {
    if (!requirements || !design) return
    void act('generate', () => request<GeneratedCode>('/api/generate', { project, requirements, service_design: design }), value => {
      setGenerated(value); setCode(value.python_code); setResult(null)
    })
  }
  const run = () => {
    if (!requirements || !design || !code.trim()) return
    void act('run', () => request<RunResult>('/api/run', {
      project, requirements, service_design: design, code,
      customer_evidence: evidence, requirements_revision: revision, parent_run_id: parentRunId
    }), value => { setResult(value); setProposal(null) })
  }
  const refine = () => {
    if (!result) return
    void act('refine', () => request<RequirementRefinementProposal>('/api/refine', {
      run_id: result.run_id, evidence
    }), setProposal)
  }
  const acceptProposal = () => {
    if (!proposal || !result) return
    setRequirements(proposal.proposed_requirements)
    setRevision(result.requirements_revision + 1)
    setParentRunId(result.run_id)
    setDesign(null); setGenerated(null); setCode(''); setResult(null); setProposal(null)
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }
  const reset = () => {
    setProject(SAMPLE); setRequirements(null); setDesign(null); setGenerated(null);
    setCode(''); setResult(null); setEvidence([]); setProposal(null);
    setRevision(0); setParentRunId(null); setError('')
  }
  const downloadJson = () => {
    if (!result) return
    const url = URL.createObjectURL(new Blob([JSON.stringify(result, null, 2)], { type: 'application/json' }))
    const anchor = document.createElement('a')
    anchor.href = url; anchor.download = `run-${result.run_id}.json`; anchor.click()
    setTimeout(() => URL.revokeObjectURL(url), 1000)
  }
  const inputReady = !!health?.ollama.reachable && !!health?.ollama.installed
  const bothReady = inputReady && !!health?.e2b_configured
  return <div className="app-shell">
    <header className="topbar"><div className="brand"><div className="logo">F<span>·</span></div><div><strong>FEASIBILITY STUDIO</strong><small>Business × Engineering × Evidence</small></div></div><div className="top-right"><span className="version">SAMPLE / v0.6</span><span className="secure">Sandbox execution + quality refinement</span></div></header>
    <main className="page">
      <div className="hero"><div className="hero-copy"><span className="eyebrow">VENTURE SUPPORT · TECHNOLOGY SELECTION GATE</span><h1>事業仮説を、<br/><em>比較可能な証拠</em>に変える。</h1><p>要件 → サービス設計 → コード生成 → E2B検証。実装の正しさと要件の妥当性を分けて記録し、要件自体の改善を人間が判断します。</p></div><div className="hero-side"><div className="hero-side-label">SYSTEM ARCHITECTURE</div><div className="architecture"><span>React + FastAPI</span><b>↓</b><span>Mac Studio · Ollama / Metal</span><b>↓</b><span>E2B · bounded repair + final holdout</span><b>↓</b><span>Independent Technical Gate</span></div></div></div>
      <section className="statusbar"><div><span className={`status-dot ${inputReady ? 'green' : 'amber'}`}/><b>Ollama · Metal</b><small>{healthError ? 'API接続不可（ポートとログを確認）' : !health ? '接続確認中' : !health.ollama.reachable ? 'Ollama接続不可' : !health.ollama.installed ? 'モデル未導入' : health.model}</small></div><div><span className={`status-dot ${health?.e2b_configured ? 'green' : 'amber'}`}/><b>E2B API</b><small>{healthError ? '状態取得不可' : !health ? '接続確認中' : health.e2b_configured ? 'キー設定済み' : 'キー未設定'}</small></div><div><span className="status-dot green"/><b>Evaluation</b><small>3方式 / DEV＋HOLDOUT</small></div><button className="button-ghost" onClick={refresh}>接続を再確認 ↻</button></section>
      {!bothReady && <div className="notice"><b>セットアップ確認：</b> OllamaはMac側で起動し、<code>qwen3-coder:30b</code> を導入してください。`.env` に <code>E2B_API_KEY</code> を設定し、必要に応じて <code>docker compose up -d --force-recreate</code>。API標準ポートは <code>18000</code> です。</div>}
      <div className="workspace"><div className="work-main">
        <section className="panel"><div className="section-title"><Step value={1} done={!!requirements}/><div><span className="kicker">DISCOVERY</span><h2>顧客要求と事業仮説</h2></div></div>
          <div className="fields"><label className="field"><span>案件名</span><input value={project.title} onChange={e => updateProject({ title: e.target.value })}/></label>
          <label className="field"><span>顧客からの相談</span><textarea className="brief" rows={6} value={project.brief} onChange={e => updateProject({ brief: e.target.value })}/><small>架空の教育SaaS案件です。実顧客の機密情報を入力しないでください。</small></label></div>
          <div className="three-inputs">
            <label className="field"><span>初期seed</span><input type="number" min={0} max={999990} value={project.seed} onChange={e => updateProject({ seed: +e.target.value })}/></label>
            <label className="field"><span>開発用seed数（1〜8）</span><input type="number" min={1} max={8} value={project.evaluation_seeds} onChange={e => updateProject({ evaluation_seeds: +e.target.value })}/></label>
            <label className="field"><span>各seedの生徒数</span><input type="number" min={4} max={40} value={project.students_count} onChange={e => updateProject({ students_count: +e.target.value })}/></label>
          </div>
          <div className="three-inputs">
            <label className="field"><span>最終評価seed数（1〜8）</span><input type="number" min={1} max={8} value={project.holdout_seeds} onChange={e => updateProject({ holdout_seeds: +e.target.value })}/><small>Qwenには非公開の別データ</small></label>
          </div>
          <div className="buttonbar"><button className="button-primary" disabled={!!busy || !inputReady} onClick={analyze}>{busy === 'analyze' ? '要件を整理中…' : 'Qwenで要件ドラフトを作成 →'}</button><button className="button-ghost" disabled={!!busy} onClick={reset}>初期値に戻す</button></div>
        </section>
        <section className="panel"><div className="section-title"><Step value={2} done={!!generated}/><div><span className="kicker">REQUIREMENTS</span><h2>要件ドラフトを人間が確認</h2></div></div>
          {!requirements ? <div className="empty">Step 1から要件を整理してください。未確認事項を確認した後に実験へ進みます。</div> : <div className="fields">
            <div className="two-inputs"><label className="field"><span>顧客課題</span><textarea rows={3} value={requirements.customer_problem} onChange={e => updateRequirement('customer_problem', e.target.value)}/></label><label className="field"><span>価値仮説</span><textarea rows={3} value={requirements.value_hypothesis} onChange={e => updateRequirement('value_hypothesis', e.target.value)}/></label></div>
            <ListEdit label="対象ユーザー" values={requirements.target_users} onChange={v => updateRequirement('target_users', v)}/>
            <ListEdit label="必須要件" values={requirements.must_have} onChange={v => updateRequirement('must_have', v)}/>
            <ListEdit label="受入基準" values={requirements.acceptance_criteria} onChange={v => updateRequirement('acceptance_criteria', v)}/>
            <div className="two-inputs"><ListEdit label="未検証の前提" values={requirements.unverified_assumptions} onChange={v => updateRequirement('unverified_assumptions', v)}/><ListEdit label="顧客への質問" values={requirements.unanswered_questions} onChange={v => updateRequirement('unanswered_questions', v)}/></div>
            <ListEdit label="次の顧客検証" values={requirements.next_customer_validation} onChange={v => updateRequirement('next_customer_validation', v)}/>
            <div className="note"><b>要件改訂 v{revision}</b><p>初期要件は仮説です。実装の成功は顧客価値の証明ではありません。受入基準は下記で AC-01, AC-02… として追跡されます。</p></div>
            <div className="buttonbar"><button className="button-primary" disabled={!!busy} onClick={designService}>{busy === 'design' ? 'サービス設計中…' : 'Qwenでサービス設計案を生成 →'}</button></div>
          </div>}
        </section>
        <section className="panel"><div className="section-title"><Step value={3} done={!!design}/><div><span className="kicker">SERVICE DESIGN</span><h2>サービス設計 — 実装前の中間表現</h2></div></div>
          {!design ? <div className="empty">要件の後にサービス設計を生成し、ユースケース・制約・代替案を人間が確認します。</div> : <div className="fields">
            <label className="field"><span>プロダクトの範囲</span><textarea rows={2} value={design.product_scope} onChange={e => updateDesign('product_scope', e.target.value)}/></label>
            <div className="two-inputs"><ListEdit label="利用者・関係者" values={design.actors} onChange={v => updateDesign('actors',v)}/><ListEdit label="ユースケース" values={design.use_cases} onChange={v => updateDesign('use_cases',v)}/></div>
            <div className="two-inputs"><ListEdit label="業務フロー" values={design.service_flow} onChange={v => updateDesign('service_flow',v)}/><ListEdit label="ドメインエンティティ" values={design.domain_entities} onChange={v => updateDesign('domain_entities',v)}/></div>
            <div className="two-inputs"><ListEdit label="ハード制約（評価器は独立して固定）" values={design.hard_constraints} onChange={v => updateDesign('hard_constraints',v)}/><ListEdit label="ソフト目的" values={design.soft_objectives} onChange={v => updateDesign('soft_objectives',v)}/></div>
            <div className="two-inputs"><ListEdit label="インターフェース" values={design.interfaces} onChange={v => updateDesign('interfaces',v)}/><ListEdit label="受入テスト案" values={design.acceptance_tests} onChange={v => updateDesign('acceptance_tests',v)}/></div>
            <div className="two-inputs"><ListEdit label="代替設計案" values={design.alternatives} onChange={v => updateDesign('alternatives',v)}/><ListEdit label="要検証の仮定" values={design.assumptions} onChange={v => updateDesign('assumptions',v)}/></div>
            <ListEdit label="顧客に確認する事項" values={design.external_validation_needed} onChange={v => updateDesign('external_validation_needed',v)}/>
            <div className="buttonbar"><button className="button-primary" disabled={!!busy} onClick={generate}>{busy === 'generate' ? '生成中…' : 'サービス設計を渡してQwenでコード生成 →'}</button></div>
          </div>}
        </section>
        <section className="panel"><div className="section-title"><Step value={4} done={!!result}/><div><span className="kicker">SANDBOX EXPERIMENT</span><h2>3方式をE2Bで比較実行</h2></div></div>
          {!generated ? <div className="empty">Step 3のサービス設計に基づいてコードを生成してください。</div> : <div className="fields">
            <div className="note"><b>Qwenが提案した方法</b><p>{generated.rationale}</p></div>
            <label className="field"><span>Qwen生成コード（編集可能）</span><textarea className="code" rows={16} spellCheck={false} value={code} onChange={e => { setCode(e.target.value); setResult(null) }}/><small>3方式はE2B内で隔離実行。採点器はFastAPI内で独立して動作します。</small></label>
            <div className="two-inputs">
              <label className="field"><span>対・厳密DP 最低効用比</span><input type="number" min={0.5} max={1} step="0.01" value={project.min_quality_ratio} onChange={e => { setProject(prev => ({ ...prev, min_quality_ratio: +e.target.value })); setResult(null) }}/></label>
              <label className="field"><span>対・Greedy 必要改善比</span><input type="number" min={1} max={1.5} step="0.01" value={project.min_improvement_ratio} onChange={e => { setProject(prev => ({ ...prev, min_improvement_ratio: +e.target.value })); setResult(null) }}/></label>
            </div>
            <label className="field"><span>機能NO-GO／品質HOLD時のコード改訂上限（0〜3）</span><input type="number" min={0} max={3} step={1} value={project.max_repair_attempts} onChange={e => { setProject(prev => ({ ...prev, max_repair_attempts: Math.max(0, Math.min(3, Number(e.target.value))) })); setResult(null) }}/><small>DEVの制約違反または品質未達で改訂。各改訂は新規E2Bで開発用seedを再実行。DEVに有効候補がある場合のみHOLDOUTで一度だけ検証します。</small></label>
            <div className="buttonbar"><button className="button-primary" disabled={!!busy || !health?.e2b_configured || !code.trim()} onClick={run}>{busy === 'run' ? 'E2Bで検証・品質改善中…' : 'E2Bで比較実験を実行 →'}</button><span className="hint">E2B SandboxはDEV参照2＋DEV候補1＋改訂ごとに追加1個。HOLDOUTは有効候補がある場合のみ追加3個。改訂はMacのOllamaで推論します。</span></div>
          </div>}
        </section>
        <section className="panel"><div className="section-title"><Step value={5} done={evidence.length > 0}/><div><span className="kicker">CUSTOMER EVIDENCE</span><h2>要件妥当性の証拠を入力（任意）</h2></div></div>
          <div className="fields"><p>合成データは事業価値の証拠に算入しません。顧客由来と申告した証拠も、出典と人間の確認がなければUNVERIFIEDです。</p>
            <div className="two-inputs"><label className="field"><span>関連する受入基準</span><select value={evidenceDraft.requirement_id} onChange={e => setEvidenceDraft(x=>({...x,requirement_id:e.target.value}))}>{(requirements?.acceptance_criteria ?? []).map((v,i)=><option key={i} value={`AC-${String(i+1).padStart(2,'0')}`}>AC-{String(i+1).padStart(2,'0')} {v.slice(0,25)}</option>)}</select></label>
            <label className="field"><span>証拠の由来</span><select value={evidenceDraft.provenance} onChange={e=>setEvidenceDraft(x=>({...x,provenance:e.target.value as CustomerEvidence['provenance']}))}><option value="synthetic">合成データ</option><option value="real_customer">実顧客</option><option value="stakeholder">社内関係者</option><option value="desk_research">公開資料</option></select></label></div>
            <div className="two-inputs"><label className="field"><span>観測の向き</span><select value={evidenceDraft.verdict} onChange={e=>setEvidenceDraft(x=>({...x,verdict:e.target.value as CustomerEvidence['verdict']}))}><option value="inconclusive">判断不能</option><option value="support">支持</option><option value="contradict">反証</option></select></label>
            <label className="field"><span>確認担当者（任意）</span><input value={evidenceDraft.reviewer} onChange={e=>setEvidenceDraft(x=>({...x,reviewer:e.target.value}))}/></label></div>
            <label className="field"><span>観測内容</span><textarea rows={2} value={evidenceDraft.observation} onChange={e=>setEvidenceDraft(x=>({...x,observation:e.target.value}))}/></label>
            <label className="field"><span>出典・リンク・ヒアリング記録ID</span><input value={evidenceDraft.source_reference} onChange={e=>setEvidenceDraft(x=>({...x,source_reference:e.target.value}))}/></label>
            <label className="field"><span><input type="checkbox" checked={evidenceDraft.human_verified} onChange={e=>setEvidenceDraft(x=>({...x,human_verified:e.target.checked}))}/> 人間が内容を確認した（自己申告）</span></label>
            <button className="button-ghost" type="button" disabled={!evidenceDraft.observation.trim()} onClick={addEvidence}>証拠台帳に追加</button>
            {evidence.map(e=><div className="note" key={e.evidence_id}><b>{e.evidence_id} · {e.requirement_id} · {e.verdict}</b><p>{e.observation} / {e.provenance} / {e.source_reference || '出典なし'}</p><button className="button-ghost" onClick={()=>setEvidence(prev=>prev.filter(x=>x.evidence_id!==e.evidence_id))}>削除</button></div>)}
          </div>
        </section>
        {error && <div className="error" role="alert"><b>処理を完了できませんでした</b><p>{error}</p></div>}
        {result && <section className="panel report-panel"><div className="section-title"><Step value={6} done={true}/><div><span className="kicker">EVIDENCE & HUMAN DECISION</span><h2>技術選定の実証結果</h2></div></div>
          <div className="evidence-table"><h3>二軸の判定 — 実装と要件</h3>
            <div className="three-candidates"><div className="candidate-card"><small>IMPLEMENTATION VALIDITY</small><strong>{result.requirement_assessment?.implementation_validity ?? 'N/A'}</strong><p>独立評価器による制約確認</p></div><div className="candidate-card"><small>REQUIREMENT VALIDITY</small><strong>{result.requirement_assessment?.requirement_validity ?? 'UNVERIFIED'}</strong><p>顧客由来の確認済み証拠による暫定判定</p></div></div>
            <table><thead><tr><th>基準</th><th>内容</th><th>要件妥当性</th></tr></thead><tbody>{result.requirement_assessment?.findings.map(f=><tr key={f.requirement_id}><td>{f.requirement_id}</td><td>{f.criterion}</td><td>{f.status}</td></tr>)}</tbody></table>
            <p>未検証は失敗ではありません。実顧客での価値検証が必要です。要件改訂 v{result.requirements_revision} / 親実行 {result.parent_run_id ?? 'なし'}</p>
            <button className="button-primary" disabled={!!busy} onClick={refine}>{busy==='refine'?'要件改善案を作成中…':'DEV結果から要件の改訂案を生成 →'}</button>
            {proposal && <div className="note"><b>要件改善案 — 承認待ち</b><p>{proposal.diagnosis.join(' / ')}</p><p>変更理由：{proposal.change_reasons.join(' / ')}</p><p>未検証：{proposal.unresolved_evidence.join(' / ')}</p>
              <details><summary>改訂案の要件JSON</summary><pre>{JSON.stringify(proposal.proposed_requirements,null,2)}</pre></details>
              <div className="buttonbar"><button className="button-primary" onClick={acceptProposal}>改訂案を採用し、設計から再検証</button><button className="button-ghost" onClick={()=>setProposal(null)}>却下</button></div>
            </div>}
          </div>
          <div className="decision"><small>FUNCTIONAL GATE</small><strong>{result.functional_gate}</strong><small>TECHNOLOGY SELECTION GATE</small><strong>{result.selection_gate}</strong><p>{result.gate_reasons.join(' ')}</p><span>BUSINESS GATE: {result.business_gate}</span></div>
          <div className="report-summary"><b>{result.holdout_executed ? `最終評価：未使用seed ${result.holdout_seeds.length} 件を評価済み` : 'HOLDOUT未実行 — DEVで有効候補なし'}</b><span>DEV {result.seeds.join(', ')} · {result.holdout_executed ? `HOLDOUT ${result.holdout_seeds.join(', ')} · 採用試行 ${result.selected_attempt_index}` : '採用試行なし・最終E2B呼び出しを省略'}</span></div>
          {result.holdout_executed && result.baseline && result.optimal && result.generated
            ? <div className="three-candidates"><CandidateCard title="A · 静的Greedy（最終）" data={result.baseline}/><CandidateCard title="B · 厳密DP（最終）" data={result.optimal}/><CandidateCard title="C · Qwen候補（最終）" data={result.generated}/></div>
            : <div className="three-candidates"><CandidateCard title="A · 静的Greedy（DEV）" data={result.development_baseline}/><CandidateCard title="B · 厳密DP（DEV）" data={result.development_optimal}/><CandidateCard title="C · Qwen最後の試行（DEV、不採用）" data={result.development_generated}/></div>}
          <div className="evidence-table"><h3>機能NO-GO／品質HOLDの改訂履歴（開発用のみ）</h3>
            <p>初回を含む {result.repair_attempts.length} 試行、最大改訂 {result.max_repair_attempts} 回。Functional PASSしたDEVコードだけを選択。全NO-GOなら候補を採用せず、HOLDOUTを実行しません。</p>
            <table><thead><tr><th>試行</th><th>判定</th><th>修正方法</th><th>成功DEV seed</th><th>代理効用</th><th>採用</th></tr></thead><tbody>
              {result.repair_attempts.map(a => <tr key={a.attempt_index}>
                <td>{a.attempt_index === 0 ? '初回' : `改訂 ${a.attempt_index}`}</td><td>{a.verdict}</td><td>{a.repair_strategy}</td>
                <td>{a.candidate.passed_seeds}/{a.candidate.total_seeds}</td><td>{format(a.candidate.score)}</td><td>{a.selected ? '✓' : ''}</td>
              </tr>)}
            </tbody></table>
            {result.repair_attempts.filter(a => a.verdict === 'NO-GO' || a.verdict === 'HOLD' || a.repair_error).map(a =>
              <details key={a.attempt_index}><summary>試行 {a.attempt_index}: {a.verdict} — 検証ログ・改善フィードバック</summary>
                {a.verdict === 'NO-GO' && <pre>{a.candidate.per_seed.filter(s => !s.hard_constraint_pass).map(s =>
                  `seed=${s.seed} sandbox=${s.sandbox_id} status=${s.status}\nviolations:\n${s.violations.join('\n')}\nstderr:\n${s.stderr || '(なし)'}\nstdout:\n${s.stdout || '(なし)'}`).join('\n\n')}</pre>}
                {a.verdict === 'HOLD' && <p>制約は充足していますが、開発用代理効用が基準を満たしませんでした。</p>}
                {Object.keys(a.error_summary).length > 0 && <p>エラー分類：{Object.entries(a.error_summary).map(([k,v]) => `${k}=${v}`).join(' / ')}</p>}
                {a.code_diff && <><strong>前試行からのコード差分</strong><pre>{a.code_diff}</pre></>}
                {a.feedback && <><strong>Qwenに渡したフィードバック（DEVのみ）</strong><pre>{a.feedback}</pre></>}
                {a.repair_error && <p className="violations">改訂モデルのエラー：{a.repair_error}</p>}
              </details>)}
          </div>
          <div className="evidence-table"><h3>開発用seedでの改善確認</h3>
            <table><thead><tr><th>DEV seed</th><th>Greedy</th><th>厳密DP</th><th>採用Qwen</th></tr></thead><tbody>
              {result.seeds.map((seed, i) => <tr key={seed}><td>{seed}</td><td>{format(result.development_baseline.per_seed[i]?.score ?? null)}</td><td>{format(result.development_optimal.per_seed[i]?.score ?? null)}</td><td>{format(result.development_generated.per_seed[i]?.score ?? null)}</td></tr>)}
            </tbody></table>
          </div>
          {result.holdout_executed && result.baseline && result.optimal && result.generated &&
            <div className="evidence-table"><h3>最終評価用seedでの独立審査（Qwenへのフィードバックなし）</h3>
              <table><thead><tr><th>HOLDOUT seed</th><th>Greedy</th><th>厳密DP</th><th>採用Qwen</th></tr></thead><tbody>
                {result.holdout_seeds.map((seed, i) => <tr key={seed}><td>{seed}</td><td>{format(result.baseline!.per_seed[i]?.score ?? null)}</td><td>{format(result.optimal!.per_seed[i]?.score ?? null)}</td><td>{format(result.generated!.per_seed[i]?.score ?? null)}</td></tr>)}
              </tbody></table>
              <p>最終評価でNO-GO/HOLDが出ても改訂せず記録します。これは合成データ上の代理効用で、実際の学習効果を意味しません。</p>
              {result.generated.per_seed.filter(s => !s.hard_constraint_pass).map(s => <details key={s.seed}><summary>最終NO-GOログ seed {s.seed}</summary><pre>{[...s.violations, s.stderr, s.stdout].filter(Boolean).join('\n')}</pre></details>)}
            </div>}
          <div className="evidence-table"><h3>学習計画プロトタイプ — {result.plan_comparisons_source === 'holdout' ? '最終評価' : '開発用'}データの具体例</h3>
            <p>同一生徒の科目別時間配分を比較。無効なQwen候補の配分はN/Aです。HOLDOUT未実行ならDEVのみを表示します。</p>
            <div className="plan-grid">{result.plan_comparisons.map(p => <PlanCard key={`${p.seed}-${p.student_id}`} plan={p} datasetLabel={result.plan_comparisons_source === 'holdout' ? 'HOLDOUT' : 'DEV'}/>)}</div>
          </div>
          <div className="business-scenario"><h3>事業シナリオ（未検証の仮定）</h3><div className="metric-grid"><div><span>月商の仮計算</span><b>{yen(result.business_scenario.monthly_revenue_yen)}</b></div><div><span>月間差額の仮計算</span><b>{yen(result.business_scenario.monthly_contribution_yen)}</b></div><div><span>単純損益分岐塾数</span><b>{result.business_scenario.break_even_schools ?? 'N/A'}</b></div></div><p>価格受容性・実際の講師負荷削減・学習成果は検証していません。</p></div>
          <div className="report-download"><div><b>Feasibility Report v0.6</b><small>実行ID {result.run_id} · DEV {result.seeds.join(', ')} · HOLDOUT {result.holdout_seeds.join(', ')} · 証跡保存</small></div><div className="download-actions"><a className="button-primary" href={`/api/reports/${result.run_id}/report.md`}>Markdownを保存 ↓</a><button className="button-ghost" onClick={downloadJson}>JSONを保存 ↓</button></div></div>
          <details className="report-preview"><summary>Markdownレポート全文</summary><pre>{result.report_markdown}</pre></details>
        </section>}
      </div>
      <aside className="side-panel"><div className="side-inner"><span className="kicker">BUSINESS ASSUMPTIONS</span><h3>事業仮説の入力</h3><p>この数値は顧客検証前の仮定であり、市場データではありません。</p>
        {([
          ['monthly_price_yen', '月額料金（円/塾）'],
          ['paying_schools', '有料契約塾数（仮定）'],
          ['monthly_operating_cost_yen', '月間運用費（円）'],
          ['hours_saved_per_school', '削減時間（時/塾）'],
          ['teacher_hourly_cost_yen', '講師時間単価（円）'],
        ] as const).map(([key, label]) => <label key={key} className="field side-field"><span>{label}</span><input type="number" min={0} value={project.business[key]} onChange={e => updateBusiness(key, +e.target.value)}/></label>)}
        <div className="scenario-preview"><small>月間売上（仮）</small><strong>{yen(project.business.monthly_price_yen * project.business.paying_schools)}</strong><small>月間差額（仮）</small><strong>{yen(project.business.monthly_price_yen * project.business.paying_schools - project.business.monthly_operating_cost_yen)}</strong></div>
        <div className="sidebar-bottom"><b>REVIEW PRINCIPLE</b><p>動くことと採用する価値は別。合成データで市場受容性を判定しません。利用前に人間が承認します。</p></div>
      </div></aside></div>
      <footer>AI VENTURE FEASIBILITY STUDIO v0.6 · Synthetic data only · Not affiliated with Sun Asterisk or its clients</footer>
    </main>
  </div>
}
