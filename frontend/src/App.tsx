import { useEffect, useState } from 'react';
import './styles.css';

type Dict = Record<string, any>;
type HistoryKind = 'runs' | 'experiments' | 'proposals' | 'benchmarks' | 'assessments' | 'policy_validations' | 'exports' | 'workflows';
const BACKEND = '/api';
const BENCHMARK_CASES: {id:string;label:string}[] = [
  {id:'fifo_sla_conflict', label:'R0が正しくても事業要件と不一致'},
  {id:'correct_fifo_no_customer_evidence',label:'顧客証拠なし（改訂を保留すべき）'},
  {id:'actual_fifo_implementation_bug',label:'本物の実装バグ（要件変更不要）'},
  {id:'conflicting_stakeholder_notes',label:'相反する模擬顧客コメント'}
];

// Mirrors the *guidance* implied by the server-side typed acceptance templates.
// The server remains authoritative; this preview is not a semantic evidence check.
type ReviewFeature = '' | 'claims_assignment' | 'claim_progress_updates';
type ReviewFeatureHint = ReviewFeature | 'ambiguous';
function reviewFeatureHint(text: string): ReviewFeatureHint {
  const h = text.toLowerCase();
  const notification = /notify|notification|notifi|update|communication|communicate|status|progress|inform|連絡|通知|進捗|状況/.test(h)
    || /(?:顧客|契約者|利用者)(?:へ|に|向けて).{0,12}報告/.test(text);
  const assignment = /assign|allocation|allocate|reviewer|triage|priorit|schedul|routing|capacity|担当|割当|振分|配分|優先順位|資格|審査員/.test(h);
  return notification && assignment ? 'ambiguous' : notification ? 'claim_progress_updates' : assignment ? 'claims_assignment' : '';
}
function assignmentHasTimeContext(text: string): boolean {
  return /delay|delayed|late|waiting|time|processing|handling|遅延|期限|処理|deadline|due date|sla|期日|締切|時間/i.test(text);
}

async function call<T>(path: string, body?: unknown): Promise<T> {
  const response = await fetch(`${BACKEND}${path}`, body === undefined ? {} : {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body),
  });
  if (!response.ok) {
    let msg = `HTTP ${response.status}`;
    try { const data = await response.json(); msg = typeof data.detail === 'string' ? data.detail : JSON.stringify(data.detail); } catch { /* ignore */ }
    throw Error(msg);
  }
  return await response.json() as T;
}

function Metric({ caption, value, subtle = false }: { caption: string; value: string | number; subtle?: boolean }) {
  return <div className="metric"><small>{caption}</small><b className={subtle ? 'small-value' : ''}>{value}</b></div>;
}
function Status({ good, children }: { good: boolean; children: React.ReactNode }) {
  return <span className={'status ' + (good ? 'pass' : 'hold')}>{children}</span>;
}
function Disclosure({ title, data }: { title: string; data: unknown }) {
  return <details><summary>{title}</summary><pre>{JSON.stringify(data, null, 2)}</pre></details>;
}
function Group({ no, title, desc, children }: { no: number; title: string; desc: string; children: React.ReactNode }) {
  return <section className="card"><header className="section-header"><div className="step-number">{no.toString().padStart(2, '0')}</div><div><h2>{title}</h2><p>{desc}</p></div></header>{children}</section>;
}

export default function App() {
  const [sample, setSample] = useState<Dict | null>(null);
  const [brief, setBrief] = useState('');
  const [seed, setSeed] = useState(42);
  const [health, setHealth] = useState<Dict | null>(null);
  const [service, setService] = useState<Dict | null>(null);
  const [r0, setR0] = useState<Dict | null>(null);
  const [proposal, setProposal] = useState<Dict | null>(null);
  const [approval, setApproval] = useState<Dict | null>(null);
  const [generated, setGenerated] = useState<Dict | null>(null);
  const [code, setCode] = useState('');
  const [experiment, setExperiment] = useState<Dict | null>(null);
  const [condition, setCondition] = useState<'counterexample' | 'control'>('counterexample');
  const [actor, setActor] = useState('Claims Product Owner (demo)');
  const [rationale, setRationale] = useState('模擬反例に基づく技術検証として、期限優先方式への改訂を承認。事業妥当性は未検証。');
  const [overrideRationale, setOverrideRationale] = useState('R0のFIFO実装は独立評価でPASS。ODAの診断はHOLDのまま残し、理由・証拠・実装認識を個別に確認する。模擬反例と固定R1契約に基づく技術検証のみ継続し、実顧客の事業妥当性は未検証として扱う。');
  const [acknowledgeOverride, setAcknowledgeOverride] = useState(false);
  const [busy, setBusy] = useState('');
  const [error, setError] = useState('');
  const [history, setHistory] = useState<Dict[]>([]);
  const [historyKind, setHistoryKind] = useState<HistoryKind>('experiments');
  const [benchmarkCases, setBenchmarkCases] = useState<string[]>(['fifo_sla_conflict', 'actual_fifo_implementation_bug']);
  const [benchmarkRepetitions, setBenchmarkRepetitions] = useState(1);
  const [benchmark, setBenchmark] = useState<Dict | null>(null);
  const [rescoreId, setRescoreId] = useState('');
  const [rescore, setRescore] = useState<Dict | null>(null);
  const [assessmentExperimentId, setAssessmentExperimentId] = useState('');
  const [assessment, setAssessment] = useState<Dict | null>(null);
  const [, setPipelineExport] = useState<Dict | null>(null);
  const [, setPolicyValidation] = useState<Dict | null>(null);
  const [fullRun, setFullRun] = useState<Dict | null>(null);
  const [fullRunId, setFullRunId] = useState('');
  const [evidenceDatasets, setEvidenceDatasets] = useState<Dict[]>([]);
  const [evidenceDataset, setEvidenceDataset] = useState<'community_credit' | 'cfpb_sample' | 'insurance_claims_uk'>('insurance_claims_uk');
  const [evidenceQuery, setEvidenceQuery] = useState('insurance claim delays poor communication processing time');
  const [ragResult, setRagResult] = useState<Dict | null>(null);
  const [datasetMeta, setDatasetMeta] = useState<Dict | null>(null);
  const [ragIndex, setRagIndex] = useState<Dict | null>(null);
  const [llmExtraction, setLlmExtraction] = useState(true);
  const [explicitReview, setExplicitReview] = useState(false);
  const [evidenceMode, setEvidenceMode] = useState<'public'|'synthetic'>('public');
  const [r1Mode, setR1Mode] = useState<'llm_only'|'skill_only'|'compare'>('compare');
  const [diagnosticRepair, setDiagnosticRepair] = useState(true);
  const [diagnosticBlind, setDiagnosticBlind] = useState(true);
  const [blindCaseCount, setBlindCaseCount] = useState(4);
  const [skillManifest, setSkillManifest] = useState<Dict | null>(null);
  const [evidenceActor, setEvidenceActor] = useState('Technical reviewer (demo)');
  const [evidenceRationale, setEvidenceRationale] = useState('公開資料を参照し、次工程では顧客未承認の検証仮説としてのみ扱う。');
  const [reviewRequirement, setReviewRequirement] = useState('');
  const [selectedEvidenceIds, setSelectedEvidenceIds] = useState<string[]>([]);
  const [evidenceReviewError, setEvidenceReviewError] = useState('');
  const [acknowledgeEvidence, setAcknowledgeEvidence] = useState(false);
  const [supportAssessment, setSupportAssessment] = useState<'supports_problem'|'context_only'|'contradicts'>('context_only');
  const [maxTotalMissed, setMaxTotalMissed] = useState(0);
  const [minReductionPct, setMinReductionPct] = useState(50);
  const [requireBehavioral, setRequireBehavioral] = useState(true);
  const [requirementType, setRequirementType] = useState<ReviewFeature>('');
  const [maxNotificationDelay, setMaxNotificationDelay] = useState(24);
  const [minNotificationCoverage, setMinNotificationCoverage] = useState(100);
  async function refreshHistory(kind: HistoryKind) {
    const result = await call<{items: Dict[]}>(`/history/${kind}`);
    setHistory(result.items);
  }

  useEffect(() => {
    call<Dict>('/sample').then(s => { setSample(s); setBrief(s.brief); setService(s.service_design_r0); }).catch(e => setError(String(e)));
    call<Dict>('/health').then(setHealth).catch(e => setError(String(e)));
    call<Dict>('/skills/claims-allocation').then(setSkillManifest).catch(e=>setError(String(e)));
    refreshHistory('experiments').catch(e => setError(String(e)));
    call<{datasets:Dict[]}>('/evidence/datasets').then(r=>setEvidenceDatasets(r.datasets)).catch(e=>setError(String(e)));
  }, []);
  // Long-running 01–09 work happens server-side. Poll persisted state so the
  // user can leave/reopen the page, and never infer success from a button click.
  useEffect(() => {
    if (!fullRun?.workflow_id || fullRun.status !== 'RUNNING') return;
    let live = true;
    const timer = window.setInterval(async () => {
      try {
        const next = await call<Dict>(`/full-run/${fullRun.workflow_id}`);
        if (!live) return;
        setFullRun(next);
        if (next.status !== 'RUNNING') {
          if (next.linked_ids?.runs) setR0(await call<Dict>(`/artifacts/runs/${next.linked_ids.runs}`));
          if (next.linked_ids?.proposals) setProposal(await call<Dict>(`/artifacts/proposals/${next.linked_ids.proposals}`));
          if (next.linked_ids?.approvals) setApproval(await call<Dict>(`/artifacts/approvals/${next.linked_ids.approvals}`));
          if (next.linked_ids?.experiments) {
            const e=await call<Dict>(`/artifacts/experiments/${next.linked_ids.experiments}`);
            setExperiment(e);setAssessmentExperimentId(e.experiment_id);
          }
          if (next.linked_ids?.benchmarks) setBenchmark(await call<Dict>(`/artifacts/benchmarks/${next.linked_ids.benchmarks}`));
          if (next.linked_ids?.assessments) setAssessment(await call<Dict>(`/artifacts/assessments/${next.linked_ids.assessments}`));
          if (next.linked_ids?.policy_validations) setPolicyValidation(await call<Dict>(`/artifacts/policy_validations/${next.linked_ids.policy_validations}`));
          if (next.service_design) setService(next.service_design);
          const datasets=await call<{datasets:Dict[]}>('/evidence/datasets');setEvidenceDatasets(datasets.datasets);
          await refreshHistory('workflows');
        }
      } catch (e) { if (live) setError(e instanceof Error ? e.message : String(e)); }
    }, 1500);
    return () => { live=false;window.clearInterval(timer);};
  }, [fullRun?.workflow_id, fullRun?.status]);
  async function action(name: string, fn: () => Promise<void>) {
    setBusy(name); setError('');
    try { await fn(); } catch (e) { setError(e instanceof Error ? e.message : String(e)); }
    finally { setBusy(''); }
  }
  function button(label: string, name: string, fn: () => Promise<void>, disabled = false, className = '') {
    return <button className={className} type="button" disabled={disabled || Boolean(busy)} onClick={() => action(name, fn)}>
      {busy === name ? '実行中…' : label}</button>;
  }
  const devR0 = r0?.development?.fifo;
  const refR0 = r0?.development?.deadline;
  const hasCounterexample = proposal?.condition === 'counterexample';
  const reviewFeatureDetected = reviewFeatureHint(reviewRequirement);
  const reviewFeatureIssue = !reviewRequirement.trim() ? '' :
    !requirementType ? '対象機能を明示的に選択してください。通知の仮説は「進捗通知」、担当者割当の仮説は「担当者割当」です。' :
    reviewFeatureDetected === 'ambiguous' ? '通知と担当者割当が混在しています。別々の要件に分けてください。' :
    reviewFeatureDetected === '' ? '要件文に「担当者割当」または「請求進捗の通知」の具体的な機能を記述してください。' :
    reviewFeatureDetected !== requirementType ?
      `分類不一致：本文は${reviewFeatureDetected === 'claim_progress_updates' ? '進捗通知' : '担当者割当'}に該当します。機能の選択を変更するか、要件文を修正してください。` :
    requirementType === 'claims_assignment' && !assignmentHasTimeContext(reviewRequirement) ?
      '担当者割当の場合は、保険請求の期限超過・遅延・処理課題を要件文に明記してください。進捗通知なら対象機能を変更してください。' : '';


  return <div className="app-shell">
    <header className="masthead">
      <div className="eyebrow">AI VENTURE FEASIBILITY STUDIO · V0.21.1</div>
      <h1>Claims Operations <span>Planner</span></h1>
      <p className="lead">German InsurTech事業開発：審査人員を増やさず、保険金請求の期限超過を減らせるか。</p>
      <div className="tags"><span>架空顧客 / 合成請求データ</span><span>Qwen3-Coder + ODA-Fin-RL-8B · Ollama / Metal</span><span>E2B isolated execution</span><span>R0 → R1 requirement refinement</span></div>
    </header>

    <section className="intro-guide" aria-labelledby="app-intro-title">
      <div className="intro-heading">
        <span className="intro-kicker">アプリガイド / WHAT THIS APP DOES</span>
        <h2 id="app-intro-title">顧客課題から、検証可能な技術提案まで</h2>
        <p>架空のドイツInsurTech企業を題材に、<strong>要件整理 → 生成コードの隔離実行 → 独立評価 → 人間の承認 → 改訂案の再検証</strong>を一つの画面で体験する、技術プリセールス向けの実証アプリです。単にコードが動くかだけでなく、<strong>実装が仕様に正しいか</strong>と<strong>仕様が業務目標に合うか</strong>を分けて扱います。</p>
      </div>
      <h3 className="intro-subtitle">主な機能と画面の進め方</h3>
      <ol className="feature-overview">
        <li><span className="feature-index">00</span><div><strong>公開資料の根拠を取得・関連性を検査</strong><p>FCA/FOS保険資料・銀行インタビュー・苦情を検索。案件領域との不一致を検出し、人間による根拠の確認を必須にします。</p></div></li>
        <li><span className="feature-index">01–02</span><div><strong>顧客課題・サービス設計</strong><p>業務目標、制約、受入テストを整理し、サービス設計案を構造化します。</p></div></li>
        <li><span className="feature-index">03</span><div><strong>R0を隔離実行</strong><p>FIFO仕様をE2Bで実行し、仕様適合性と合成KPIを独立評価します。</p></div></li>
        <li><span className="feature-index">04–05</span><div><strong>二つのLLM診断・人間承認</strong><p>QwenとODAの診断を比較し、要件改訂の可否を人間が判断します。</p></div></li>
        <li><span className="feature-index">06</span><div><strong>R1の生成・修復・HOLDOUT評価</strong><p>制約を保ったコードを生成し、DEV修復後、非開示データで比較します。</p></div></li>
        <li><span className="feature-index">07</span><div><strong>履歴・監査証跡</strong><p>コード、ログ、採点結果、承認記録を参照・ZIP取得できます。</p></div></li>
        <li><span className="feature-index">08</span><div><strong>診断品質ベンチマーク</strong><p>合成ケースを用い、原因分類・証拠参照・説明の整合性を比較します。</p></div></li>
        <li><span className="feature-index">09</span><div><strong>事業価値 × AIデリバリー評価</strong><p>KPI改善とR1仕様適合を区別し、診断品質・本番未検証事項を保守的に評価します。</p></div></li>
        <li><span className="feature-index">10</span><div><strong>00〜09を一括実行してZIP保存</strong><p>保険の公開資料を検索→課題との関連性を検査→人間設定のKPI契約→固定の合成R0/R1検証。領域不一致は遮断し、原本もZIPへ保存します。</p></div></li>
      </ol>
      <div className="evidence-explainer" aria-labelledby="evidence-title">
        <div className="evidence-heading">
          <span className="intro-kicker">証拠と判断の違い</span>
          <h3 id="evidence-title">証拠IDの正確性 ≠ 証拠の妥当性 ≠ 診断の正しさ</h3>
          <p>三つは別々に確認する必要があります。IDが一致しても、根拠の信頼性や結論の正しさは保証されません。</p>
        </div>
        <div className="evidence-grid">
          <div className="evidence-item"><span className="evidence-number">1</span><strong>証拠IDの正確性</strong><p>モデルが参照したIDが入力に存在し、対象の資料に対応しているか。例：<code>SIM-SLA-001</code> は本アプリが定義した<strong>架空の識別子</strong>です。</p></div>
          <div className="evidence-item"><span className="evidence-number">2</span><strong>証拠の妥当性</strong><p>データの出所・品質・条件が、主張の根拠に適切か。現状の証拠は合成データであり、<strong>実顧客の裏付けはありません</strong>。</p></div>
          <div className="evidence-item"><span className="evidence-number">3</span><strong>診断の正しさ</strong><p>証拠から結論が論理的に導かれるか。例えば「FIFOが仕様どおりに動くこと」と「期限超過を減らせること」は別の評価です。</p></div>
        </div>
        <p className="evidence-footnote">このアプリが自動確認できるのは、主に参照IDの整合性や事前定義した合成ケース上の検証です。証拠の実世界での妥当性・診断の意味論的正しさ・EU法令適合は保証しません。</p>
      </div>
    </section>

    <div className="notice"><strong>検証対象は業務リソース配分のみ。</strong>保険金の支払可否・不正検知・法的判断は自動化しません。架空シナリオの結果は、顧客価値・規制適合・事業化を証明しません。</div>
    <div className="top-stats">
      <Metric caption="E2B API key" value={health?.e2b_configured ? 'Configured' : 'Missing'} subtle />
      <Metric caption="Mac Ollama" value={health?.ollama?.reachable ? 'Reachable' : 'Unavailable'} subtle />
      <Metric caption="Qwen model" value={health?.ollama?.model || 'qwen3-coder:30b'} subtle />
      <Metric caption="ODA-Fin-RL-8B (Vertical)" value={health?.ollama?.finance_model_installed ? 'Installed' : 'Not installed'} subtle />
      <Metric caption="要件の妥当性" value="UNVERIFIED" subtle />
    </div>

    {!health?.ollama?.finance_model_installed && health && <div className="notice">
      <strong>Vertical FM未準備:</strong> MacのOllamaで <code>ollama pull hf.co/alexsabaka/ODA-Fin-RL-8B-GGUF:Q4_K_M</code> を実行してください。
      自動的にQwenへフォールバックしません。
    </div>}
    {error && <div className="error" role="alert"><strong>エラー:</strong> {error}</div>}
    {busy && <p className="running">{busy} 実行中。大きなQwenモデルとE2Bの処理には時間がかかる場合があります。</p>}

    <section className="card evidence-rag-panel" aria-labelledby="evidence-rag-title">
      <header className="section-header"><div className="step-number">00</div><div>
        <h2 id="evidence-rag-title">Evidence-grounded Requirements RAG</h2>
        <p>公表された保険請求業務の問題背景や金融サービス利用者の発言を検索します。銀行資料を保険業務の要件根拠と誤認しないよう領域も判定します。</p>
      </div></header>
      <div className="notice"><strong>問題背景 ≠ 原因の証明 ≠ 顧客要件。</strong>FCA・FOSの公開資料は保険請求の遅延等の問題を示しますが、FIFO・資格配分が原因だとは証明しません。銀行向けインタビューは保険の業務設計の根拠として利用できません。出所・利用条件を確認してください。</div>
      <label htmlFor="evidence-dataset">取得する公開金融データ</label>
      <select id="evidence-dataset" value={evidenceDataset} onChange={e=>{setEvidenceDataset(e.target.value as 'community_credit'|'cfpb_sample'|'insurance_claims_uk');setDatasetMeta(null);setRagIndex(null);setRagResult(null);}}>
        {evidenceDatasets.length ? evidenceDatasets.map((x:Dict)=><option value={x.id} key={x.id}>{x.title}</option>) : <><option value="insurance_claims_uk">FCA/FOS — UK insurance claim handling</option><option value="community_credit">Community Credit interviews (banking)</option><option value="cfpb_sample">CFPB complaints sample (banking)</option></>}
      </select>
      <p className="muted">{evidenceDatasets.find((x:Dict)=>x.id===evidenceDataset)?.notice}</p>
      <p className="muted"><a target="_blank" rel="noreferrer" href={evidenceDatasets.find((x:Dict)=>x.id===evidenceDataset)?.source || 'https://zenodo.org/records/10425908'}>配布元・利用条件を確認</a></p>
      <div className="button-row">
        {button('データセットを取得（アプリへ保存）','evidence-download',async()=>{
          const x=await call<Dict>('/evidence/download',{dataset_id:evidenceDataset});setDatasetMeta(x);
          const d=await call<{datasets:Dict[]}>('/evidence/datasets');setEvidenceDatasets(d.datasets);
        })}
        <a className="download-link" href={`${BACKEND}/evidence/datasets/${evidenceDataset}/download`} download>取得済みデータセットを別ZIPでダウンロード</a>
        {button('検索インデックスを構築','evidence-index',async()=>{const x=await call<Dict>('/evidence/index',{dataset_id:evidenceDataset});setRagIndex(x);})}
      </div>
      {datasetMeta && <Disclosure title="ダウンロード出所とSHA256" data={datasetMeta}/>}
      {ragIndex && <p className="muted">{ragIndex.chunk_count} passages indexed / {ragIndex.method}</p>}
      <label htmlFor="rag-query">事業課題を検索する質問・キーワード</label>
      <textarea id="rag-query" rows={2} value={evidenceQuery} onChange={e=>setEvidenceQuery(e.target.value)}/>
      <label className="radio"><input type="checkbox" checked={llmExtraction} onChange={e=>setLlmExtraction(e.target.checked)}/>Qwenで根拠付き要求仮説を追加抽出（モデルは提案のみ、意味的な正しさは未検証）</label>
      <div className="button-row">{button('検索・根拠付き要求候補を生成','rag',async()=>{
        const x=await call<Dict>('/evidence/requirements',{dataset_id:evidenceDataset,query:evidenceQuery,llm_extraction:llmExtraction});setRagResult(x);
      },evidenceQuery.trim().length<3)}</div>
      {ragResult && <div className="assessment-report">
        <div className="assessment-report-head"><div><h3>Retrieved Evidence / Requirement Candidates</h3>
        <p className="muted">{ragResult.rag_id} / 元資料へのポインタを検証済み、意味的支持関係は未検証</p></div><Status good={false}>REQUIRES VALIDATION</Status></div>
        <div className="evidence-register">{ragResult.evidence?.map((e:Dict)=><div key={e.evidence_id}>
          <strong>{e.evidence_id} — {e.source_file}</strong><p>{e.quote}</p>
          <small>chars {e.start_char}–{e.end_char} / {e.source_type}（HTML資料は抽出テキスト基準の位置）</small>
          <small>support: {e.support_status} / validity: {e.validity}</small>
        </div>)}</div>
        <Disclosure title="課題との関連性・要件候補・未検証項目" data={{topic_alignment:ragResult.topic_alignment,candidates:ragResult.requirement_candidates,evaluation:ragResult.evaluation}}/>
        {ragResult.llm_suggestions && <Disclosure title="Qwenが生成した要求仮説（必ず人間が検証）" data={ragResult.llm_suggestions}/>}
        <a className="download-link" href={`${BACKEND}/evidence/results/${ragResult.rag_id}/bundle`}>RAG根拠・要求候補のZIPを保存</a>
        <p className="muted">10の公開データモードは、ここを事前に操作しなくても、ダウンロード・索引化・検索を新たに実行します。人間が根拠を選んで承認した仮説だけを01の文脈に反映します。</p>
      </div>}
    </section>

    <Group no={1} title="顧客課題・価値仮説" desc="想定顧客はドイツの保険業務SaaS企業。多国展開は仮説であり、既存顧客を示すものではありません。">
      <label htmlFor="brief">顧客ブリーフ（編集可能）</label>
      <textarea id="brief" rows={5} value={brief} onChange={e => { setBrief(e.target.value); setR0(null); setProposal(null); setApproval(null); setExperiment(null);setAssessment(null);setAssessmentExperimentId(''); }} />
      <div className="two-cols">
        <div><label htmlFor="seed">初期 DEV seed</label><input id="seed" type="number" value={seed} min="0" max="9999" onChange={e => setSeed(Number(e.target.value))}/></div>
        <div><label>主KPI</label><p className="callout">期限超過件数 ↓ / 審査総稼働時間は同一</p></div>
      </div>
      {sample && <Disclosure title="R0・R1契約と事業仮説を表示" data={{R0: sample.contract_r0,R1:sample.contract_r1, business:sample.business_hypotheses_eur}}/>}
    </Group>

    <Group no={2} title="サービス設計（中間表現）" desc="要件→ユースケース→データモデル→制約→受入テストを構造化。LLMの出力は人間未承認ドラフトです。">
      <div className="button-row">
        {button('Qwenでサービス設計案を生成', 'design', async () => { const x=await call<Dict>('/design',{brief,version:'r0'});setService(x.service_design); })}
        <button className="secondary" onClick={() => setService(sample?.service_design_r0)} disabled={!sample || !!busy}>固定サービス設計へ戻す</button>
      </div>
      <details open><summary>現在のサービス設計（JSON）</summary><pre>{JSON.stringify(service, null, 2)}</pre></details>
    </Group>

    <Group no={3} title="R0 — FIFOをE2Bで実行" desc="現在の仕様が正しく実装されていることを先に確かめます。FIFOと期限優先の固定参照方式を同一データで比較します。">
      <div className="button-row">{button('R0を実行（E2B）', 'r0', async ()=> {const x=await call<Dict>('/run-r0',{brief,seed,service_design:service});setR0(x);setProposal(null);setApproval(null);setGenerated(null);setCode('');setExperiment(null);setAssessment(null);setAssessmentExperimentId('');})}</div>
      {r0 && <>
        <div className="top-stats"><Metric caption="R0 / DEV 期限超過" value={devR0?.missed_total ?? '—'}/><Metric caption="期限優先 / DEV 期限超過" value={refR0?.missed_total ?? '—'}/><Metric caption="R0 / DEV 割当予定時間" value={devR0?.worked_hours_total ?? '—'}/><Metric caption="実装の正しさ" value={r0.implementation_validity}/></div>
        <Status good={r0.implementation_validity === 'PASS'}>{r0.implementation_validity === 'PASS' ? 'FIFO specification PASS' : 'FAIL'}</Status>
        <a href={`${BACKEND}/runs/${r0.run_id}/report`} target="_blank" rel="noreferrer">R0技術レポート（Markdown）</a>
        <a className="download-link" href={`${BACKEND}/artifacts/runs/${r0.run_id}/bundle`}>R0の全証跡 ZIP</a>
        <Disclosure title="R0 DEV/HOLDOUTの実行根拠" data={{seeds:r0.dev_seeds,holdout:r0.holdout_seeds,development:r0.development,holdout_results:r0.holdout}}/>
      </>}
    </Group>

    <Group no={4} title="Qwen × ODA-Fin-RL-8B：独立の要件診断" desc="同じDEV結果と模擬証拠を2モデルへ独立に渡します。ODAの根本原因分類・説明・改訂案はQwenを参照しません。HOLDOUTは非開示です。">
      <div className="two-cols"><label className="radio"><input type="radio" checked={condition==='counterexample'} onChange={()=>setCondition('counterexample')}/>模擬反例 SIM-SLA-001を与える</label><label className="radio"><input type="radio" checked={condition==='control'} onChange={()=>setCondition('control')}/>対照：顧客証拠なし</label></div>
      <div className="button-row">{button('QwenとODAで独立診断', 'propose', async ()=>{const x=await call<Dict>('/propose',{r0_run_id:r0?.run_id || '',evidence_condition:condition,enable_repair:diagnosticRepair});setProposal(x);setApproval(null);setExperiment(null);setAssessment(null);setAssessmentExperimentId('');}, !r0)}</div>
      {proposal && <>
        <div className="status-row"><Status good={proposal.diagnosis_matches_rubric}>{proposal.diagnosis_matches_rubric?'診断ルーブリック PASS':'診断ルーブリック未達'}</Status><span className="muted">{proposal.diagnosis?.classification}</span></div>
        <div className="two-cols">
          <div className="diagnosis-panel"><h3>Qwen3-Coder（比較用）</h3>
            <Status good={proposal.diagnosis_matches_rubric}>{proposal.diagnosis_matches_rubric ? '診断PASS' : 'HOLD'}</Status>
            <p><strong>分類:</strong> {proposal.diagnosis?.classification}</p><p>{proposal.diagnosis?.reasoning}</p>
            <p><strong>改訂案:</strong> {proposal.diagnosis?.suggested_requirement_change}</p></div>
          <div className="diagnosis-panel"><h3>ODA-Fin-RL-8B（Vertical FM）</h3>
            <Status good={proposal.finance_diagnosis_matches_rubric}>{proposal.finance_diagnosis_matches_rubric ? '独立ルーブリックPASS' : 'HOLD'}</Status>
            <p><strong>分類:</strong> {proposal.finance_diagnosis?.classification}</p>
            <p><strong>R0実装:</strong> {proposal.finance_diagnosis?.r0_implementation_assessment}</p>
            <p><strong>要件と事業KPI:</strong> {proposal.finance_diagnosis?.business_requirement_assessment}</p>
            <p><strong>根本原因:</strong> {proposal.finance_diagnosis?.root_cause}</p>
            <p><strong>改訂案:</strong> {proposal.finance_diagnosis?.suggested_requirement_change}</p>
            <Disclosure title="残る不確実性・業務トレードオフ・規制確認事項" data={{tradeoffs:proposal.finance_diagnosis?.business_tradeoffs, compliance_questions:proposal.finance_diagnosis?.compliance_questions, uncertainty:proposal.finance_diagnosis?.remaining_uncertainty, rubric_failures:proposal.finance_diagnosis_rubric_failures}}/>
          </div>
        </div>
        <div className="two-cols">
          <Disclosure title="Qwenの独立診断品質（詳細・失敗コード）" data={proposal.qwen_diagnostic_quality || {note:'旧保存結果：再採点機能を利用'}} />
          <Disclosure title="ODAの独立診断品質（詳細・失敗コード）" data={proposal.oda_diagnostic_quality || {note:'旧保存結果：再採点機能を利用'}} />
        </div>
        {proposal.diagnostic_repair?.enabled && <Disclosure title="v0.21 初回診断と再診断の区別（初回PASS率・再試行を保存）" data={{initial:proposal.diagnostic_initial_scores,revisions:proposal.diagnostic_repair}}/>}
        <p className="muted">合成反例と要件の適合: {proposal.synthetic_requirement_fit || '未判定'} ／ 実顧客における妥当性: UNVERIFIED。</p>
        <p className="muted">モデル間の分類ラベル一致（説明の一致ではありません）: {String(proposal.model_comparison?.classification_agreement)}。ODAの規制見解は一次資料検証を行っていないため事業承認の根拠にはしません。</p>
        <a className="download-link" href={`${BACKEND}/artifacts/proposals/${proposal.proposal_id}/bundle`}>診断結果・根拠のJSON ZIPを保存</a>
        <Disclosure title="証拠・R0/R1契約差分・検証不能事項" data={proposal}/>
      </>}
    </Group>

    <Group no={5} title="R1への改訂を人間が承認" desc="LLMは提案するだけで、要件・独立評価器は勝手に変更されません。">
      <div className="two-cols"><div><label htmlFor="actor">承認者名（デモ）</label><input id="actor" value={actor} onChange={e=>setActor(e.target.value)}/></div><div><label htmlFor="rationale">承認理由</label><input id="rationale" value={rationale} onChange={e=>setRationale(e.target.value)}/></div></div>
      <div className="button-row">{button('R1要件を承認する', 'approve', async()=>{const x=await call<Dict>('/approve',{proposal_id:proposal?.proposal_id || '',actor,rationale,decision:'approved'});setApproval(x);}, !proposal || !hasCounterexample || !proposal.finance_diagnosis_matches_rubric || !!approval)}
        {button('改訂案を却下する', 'reject', async()=>{const x=await call<Dict>('/approve',{proposal_id:proposal?.proposal_id || '',actor,rationale,decision:'rejected'});setApproval(x);}, !proposal || !!approval, 'secondary')}
      </div>
      {proposal && !proposal.finance_diagnosis_matches_rubric && <div className="notice">
        <strong>ODAの診断はHOLDです。</strong> R0実装は独立評価でPASSしており、モデルの実装認識・証拠ID・説明または改訂案の整合性が品質ルーブリックに未達のため通常承認を停止しています。
        診断をPASSに書き換えず、人間が反例と固定R1契約をレビューした記録を残して技術実験だけ継続できます。
        <p><strong>HOLD理由:</strong> {JSON.stringify(proposal.finance_diagnosis_rubric_failures)}</p>
        <label htmlFor="override-rationale">誤診の確認と継続の理由（ログへ保存）</label>
        <textarea id="override-rationale" rows={4} value={overrideRationale} onChange={e=>setOverrideRationale(e.target.value)} />
        <label className="radio"><input type="checkbox" checked={acknowledgeOverride} onChange={e=>setAcknowledgeOverride(e.target.checked)} />R0独立評価PASSと模擬証拠を確認しました。ODAのHOLDを残し、実顧客の事業妥当性は未検証として扱います。</label>
        <div className="button-row">{button('人間のHOLD審査を記録してR1検証へ進む', 'approve-held', async()=>{
          const x=await call<Dict>('/approve',{proposal_id:proposal?.proposal_id || '',actor,rationale,decision:'approved',domain_review_override:true,override_rationale:overrideRationale,acknowledges_independent_r0_pass:acknowledgeOverride});setApproval(x);
        }, !hasCounterexample || !!approval || !acknowledgeOverride || overrideRationale.trim().length < 20 || actor.trim().length < 2)}</div>
      </div>}
      {approval && <p><Status good={approval.decision==='approved'}>{approval.decision.toUpperCase()}</Status> <span className="muted">{approval.timestamp_utc} · {approval.actor} · {approval.approval_path}</span></p>}
    </Group>

    <Group no={6} title="R1 — LLM・Domain Skillの独立E2B評価" desc="Qwenのコード生成と、人間が作成したClaims Allocation Skillを同じ固定DEV・HOLDOUT条件で比較します。">
      <label htmlFor="r1-mode">R1実装方式（手動と10の一括実行で共通）</label>
      <select id="r1-mode" value={r1Mode} onChange={e=>setR1Mode(e.target.value as 'llm_only'|'skill_only'|'compare')}>
        <option value="compare">比較：LLM生成 + Domain Skill（推奨）</option>
        <option value="llm_only">LLM単独生成・修復</option>
        <option value="skill_only">Domain Skillのみ（R1コード生成は不要）</option>
      </select>
      <p className="muted">Skillは固定・検証可能な専門コードです。LLMが書いたコードと混同しません。DEVで選別後、未使用HOLDOUTを実行します。bounded_beamは厳密最適化ではありません。</p>
      {skillManifest && <Disclosure title="Claims Allocation Skill の構成・ハッシュ・独立評価器" data={skillManifest}/>}
      <div className="button-row">{button('R1コードを生成', 'generate-r1', async()=>{const x=await call<Dict>('/generate-r1',{approval_id:approval?.approval_id || ''});setGenerated(x);setCode(x.python_code);}, r1Mode==='skill_only' || !approval || approval.decision !== 'approved')}</div>
      {r1Mode==='skill_only' && <div className="button-row">{button('Domain SkillをE2Bで評価する','evaluate-skill',async()=>{const x=await call<Dict>('/evaluate-r1',{approval_id:approval?.approval_id || '',python_code:'',max_repairs:0,r1_mode:'skill_only'});setExperiment(x);setAssessmentExperimentId(x.experiment_id);setAssessment(null);},!approval || approval.decision!=='approved' || !!experiment)}</div>}
      {generated && r1Mode!=='skill_only' && <><p>{generated.rationale}</p><label htmlFor="code">生成コード（実行前に確認・編集可）</label><textarea className="code-editor" id="code" rows={17} spellCheck={false} value={code} onChange={e=>setCode(e.target.value)}/>
        <div className="button-row">{button('E2BでR1を独立評価する', 'evaluate-r1', async()=>{const x=await call<Dict>('/evaluate-r1',{approval_id:approval?.approval_id || '',python_code:code,max_repairs:2,r1_mode:r1Mode});setExperiment(x);setAssessmentExperimentId(x.experiment_id);setAssessment(null);}, !code || !!experiment)}</div>
      </>}
      {experiment && <>
        <div className="result-head"><Status good={experiment.r1_independent_kpi_improvement_pass}>{experiment.r1_independent_kpi_improvement_pass ? (experiment.selected_engine==='llm_generated' ? 'LLM R1 KPI PASS (synthetic)' : 'Pinned Skill R1 KPI PASS (synthetic; NOT LLM)') : 'TECHNICAL HOLD / NO-GO'}</Status><Status good={false}>REAL-WORLD REQUIREMENTS UNVERIFIED</Status></div>
        <div className="top-stats"><Metric caption="R1独立HOLDOUT" value={experiment.holdout_executed?'Executed':'Not executed'} subtle/>
          <Metric caption="FIFO 期限超過" value={experiment.holdout?.fifo?.reduce((s:number,m:Dict)=>s+(m.missed_deadlines??0),0)??'—'}/>
          <Metric caption="選択R1 期限超過" value={experiment.holdout?.generated?.reduce((s:number,m:Dict)=>s+(m.missed_deadlines??0),0)??'—'}/>
          <Metric caption="改訂コード試行数" value={experiment.attempts?.length??0}/>
        </div>
        <p className="notice"><strong>DEV採用エンジン:</strong> {experiment.selected_engine || '適格候補なし'} ／ 出典: {experiment.selected_source_provenance || 'NONE'}。Skill採用はLLMの生成成功ではありません。</p>
        {experiment.skill_comparison?.length>0 && <div className="assessment-item"><h4>Domain SkillとLLMのDEV比較</h4><div className="evidence-register">{experiment.skill_comparison.map((c:Dict)=><div key={c.engine}><strong>{c.engine}</strong><p>DEV期限超過：{c.dev?.missed_total} ／ DEV適格：{String(c.selection_gate?.eligible)} ／ E2B実行：{c.sandbox_execution_seconds}s</p><small>独立DEVゲート: {c.selection_gate?.reasons?.join(', ') || 'PASS'}。生成モデルのコストは未計測。</small></div>)}</div><Disclosure title="DEV選択後の独立HOLDOUT比較（合格候補のみ）" data={experiment.holdout_comparators || {}}/></div>}
        <a href={`${BACKEND}/experiments/${experiment.experiment_id}/report`} target="_blank" rel="noreferrer">R0/R1比較・要件改訂監査レポート（Markdown）</a>
        <a className="download-link" href={`${BACKEND}/artifacts/experiments/${experiment.experiment_id}/bundle`}>すべての生成コード・差分・E2Bログ・承認・評価をZIP保存</a>
        <Disclosure title="R1のDEV・HOLDOUT・証拠と承認履歴" data={experiment}/>
      </>}
    </Group>

    <Group no={7} title="保存した実験と監査証跡" desc="Docker bind mount: ./artifacts に保存。ブラウザから過去の結果を再表示・ZIP保存できます。">
      <div className="button-row">
        <select aria-label="履歴の種類" value={historyKind} onChange={e => { const k=e.target.value as HistoryKind; setHistoryKind(k); action('history',()=>refreshHistory(k)); }}>
          <option value="experiments">R1比較実験</option><option value="runs">R0実行</option><option value="proposals">Qwen / ODA診断</option><option value="benchmarks">診断比較ベンチマーク</option><option value="assessments">事業・デリバリー評価</option><option value="policy_validations">R1仕様・ストレス評価</option><option value="exports">旧・追加検証ZIPの履歴</option><option value="workflows">00〜09一括実行の履歴</option>
        </select>
        {button('保存履歴を更新', 'history', ()=>refreshHistory(historyKind))}
      </div>
      <div className="history-list">{history.length ? history.map(h=><div className="history-row" key={h.id}>
        <span><b>{h.id.substring(0,8)}</b> <small>{h.created_at}</small> <small>({h.files} files)</small></span>
        <span className="button-row"><button type="button" className="secondary" disabled={!!busy} onClick={()=>action('load-artifact',async()=>{
          const obj=await call<Dict>(`/artifacts/${historyKind}/${h.id}`);
          if(historyKind==='experiments'){setExperiment(obj);setAssessmentExperimentId(obj.experiment_id);setAssessment(null);}else if(historyKind==='assessments'){setAssessment(obj);setAssessmentExperimentId(obj.experiment_id);}else if(historyKind==='runs')setR0(obj);else if(historyKind==='benchmarks')setBenchmark(obj);else if(historyKind==='policy_validations')setPolicyValidation(obj);else if(historyKind==='exports')setPipelineExport({export_id:obj.export_id,status:obj.status,manifest:obj,bundle_url:`/api/exports/${obj.export_id}/bundle`});else if(historyKind==='workflows'){setFullRun(await call<Dict>(`/full-run/${h.id}`));setFullRunId(h.id);setExplicitReview(false);}else setProposal(obj);
        })}>結果を見る</button>
        <a className="download-link" href={historyKind==='workflows'?`${BACKEND}/full-run/${h.id}/bundle`:historyKind==='exports'?`${BACKEND}/exports/${h.id}/bundle`:`${BACKEND}/artifacts/${historyKind}/${h.id}/bundle`}>証跡ZIP</a></span>
      </div>) : <p className="muted">保存された実験はまだありません。</p>}</div>
    </Group>

    <Group no={8} title="診断品質ベンチマーク：Qwen vs ODA" desc="同じスキーマ・同じ合成入力で、原因分類・論理的一貫性・証拠ID・要件改訂案を別々に採点します。実顧客の正しさは判定しません。">
      <div className="notice">R0→R1の本番デモとは独立した、要件診断のみの比較です。独立した固定正解ラベルはモデルへ渡しません。コード生成・E2B実行の比較ではありません。</div>
      <div className="two-cols">
        <div><h3>合成診断シナリオ</h3>
          {BENCHMARK_CASES.map(x=><label key={x.id} className="radio"><input type="checkbox" checked={benchmarkCases.includes(x.id)} onChange={e=>setBenchmarkCases(p=>e.target.checked?[...p,x.id]:p.filter(c=>c!==x.id))}/>{x.label}</label>)}
        </div>
        <div><label htmlFor="repeats">各モデル・各シナリオの独立実行回数</label>
          <select id="repeats" value={benchmarkRepetitions} onChange={e=>setBenchmarkRepetitions(Number(e.target.value))}>
            <option value={1}>1回（動作確認）</option><option value={2}>2回</option><option value={3}>3回（出力のばらつきも確認）</option>
          </select>
          <label className="radio"><input type="checkbox" checked={diagnosticRepair} onChange={e=>setDiagnosticRepair(e.target.checked)}/>ルーブリックでHOLDなら入力事実だけを使って1回再診断（初回判定も保存）</label>
          <label className="radio"><input type="checkbox" checked={diagnosticBlind} onChange={e=>setDiagnosticBlind(e.target.checked)}/>未使用の合成診断ケース2件を初回のみで独立評価（再診断なし）</label>
          <p className="muted">通常 {benchmarkCases.length * benchmarkRepetitions * 2} 回、修復有効時は不合格ごとに最大1回追加、別ケース評価は4回追加。MacのOllamaでは直列に実行します。</p>
          <div className="button-row">{button('QwenとODAの診断品質を比較', 'run-benchmark', async()=>{
              const x=await call<Dict>('/diagnostic-benchmark/run',{case_ids:benchmarkCases,repetitions:benchmarkRepetitions,enable_repair:diagnosticRepair,blind_generalization:diagnosticBlind});setBenchmark(x);
            }, benchmarkCases.length===0)}</div>
        </div>
      </div>
      {benchmark && <>
        <p><Status good={benchmark.status==='COMPLETED'}>{benchmark.status}</Status>　<span className="muted">{benchmark.benchmark_id}</span></p>
        <div className="two-cols">
          {(['coding','finance'] as const).map(role=><div className="diagnosis-panel" key={role}>
            <h3>{role==='coding'?'Qwen3-Coder':'ODA-Fin-RL-8B'}</h3>
            <p>採点完了: {benchmark.summary?.[role]?.completed}/{benchmark.summary?.[role]?.planned}</p>
            <p>初回PASS: {benchmark.summary?.[role]?.initial_passed ?? '—'} / {benchmark.summary?.[role]?.planned}</p>
            <p>再診断後PASS: {benchmark.summary?.[role]?.passed} / {benchmark.summary?.[role]?.planned}</p>
            {benchmark.blind_generalization?.enabled && <p>別ケース初回PASS: {benchmark.blind_generalization?.summary?.[role]?.passed ?? '—'} / {benchmark.blind_generalization?.summary?.[role]?.planned ?? '—'}</p>}
            <p>基準別平均点: {benchmark.summary?.[role]?.mean_score ?? '—'}</p>
          </div>)}
        </div>
        <a href={`${BACKEND}/diagnostic-benchmark/${benchmark.benchmark_id}/report`} target="_blank" rel="noreferrer">比較レポート（Markdown）</a>
        <a className="download-link" href={`${BACKEND}/artifacts/benchmarks/${benchmark.benchmark_id}/bundle`}>全モデル診断・採点・エラーの証跡ZIP</a>
        <Disclosure title="全試行の失敗コードと採点根拠" data={benchmark.trials}/>
      </>}
      <div className="notice"><strong>過去v0.9.1の診断を非破壊で再採点</strong>
        <p className="muted">既存のproposal_idを入力します。過去の診断・承認ログは変更されません。</p>
        <div className="button-row"><input aria-label="保存済みproposal ID" placeholder="proposal UUID" value={rescoreId} onChange={e=>setRescoreId(e.target.value)}/>
        {button('旧診断を再採点', 'rescore',async()=>{
          const x=await call<Dict>(`/diagnostic-benchmark/rescore/${rescoreId.trim()}`);setRescore(x);
        }, !rescoreId.trim())}</div>
        {rescore && <Disclosure title="再採点結果：旧ルーブリック vs v0.10" data={rescore}/>}</div>
    </Group>

    <Group no={9} title="Business & Delivery Assessment — 意思決定レポート" desc="保存済みR1実験を事業価値とAIデリバリーの2軸で評価します。固定ルーブリックで採点し、LLMには採点を委ねません。">
      <div className="notice"><strong>実顧客の事業GOではありません。</strong> 合成HOLDOUTの技術結果・診断の品質・人間のデモ承認を個別に扱います。顧客需要・価格・ROI・GDPR・運用適合は証拠がない限り <strong>UNVERIFIED</strong> です。</div>
      <div className="assessment-source">
        <div>
          <label htmlFor="assessment-experiment-id">評価対象の保存済みR1実験ID</label>
          <input id="assessment-experiment-id" value={assessmentExperimentId} placeholder="experiment UUID — 06の実行結果または07の履歴から選択" onChange={e=>{setAssessmentExperimentId(e.target.value);setAssessment(null);}} />
          <p className="muted">06でR1を実行すると自動入力されます。過去の結果は07「保存した実験」から「結果を見る」を選択できます。LLMやE2Bを再実行せずに評価します。</p>
        </div>
        <div className="button-row">{button('Generate Business Assessment', 'business-assessment', async()=>{
          const result=await call<Dict>('/business-assessment/run',{experiment_id:assessmentExperimentId.trim()});setAssessment(result);
          setHistoryKind('assessments');await refreshHistory('assessments');
        }, !assessmentExperimentId.trim())}</div>
      </div>
      {assessment && <section className="assessment-report" aria-label="Project Feasibility Assessment">
        <div className="assessment-report-head">
          <div><span className="intro-kicker">DECISION REPORT / {assessment.rubric_version}</span><h3>Project Feasibility Assessment</h3><p className="muted">Experiment: {assessment.experiment_id} · {assessment.created_at}</p></div>
          <Status good={assessment.decision?.status==='GO'}>{assessment.decision?.status || 'HOLD'} / {assessment.decision?.stage || 'TECHNICAL_VALIDATION'}</Status>
        </div>
        <p>{assessment.decision?.description}</p>
        <div className="notice"><strong>Production: NO-GO</strong> — 顧客の支払意思・実業務への有効性・運用/法規制は未検証。モデル診断のHOLDは、人間が技術検証を承認しても消えません。</div>
        <div className="top-stats">
          <Metric caption="合成FIFO期限超過" value={assessment.summary_metrics?.fifo?.missed ?? '—'}/>
          <Metric caption="合成R1期限超過" value={assessment.summary_metrics?.generated?.missed ?? '—'}/>
          <Metric caption="同一稼働で改善" value={assessment.summary_metrics?.fixed_hours_and_deadline_improvement ? 'YES' : 'NO'} subtle/>
          <Metric caption="R1行動プローブ" value={assessment.summary_metrics?.behavioral_contract_pass ? 'PASS' : 'HOLD'} subtle/>
        </div>
        {assessment.axes?.map((axis:Dict)=><div className="assessment-axis" key={axis.id}>
          <h4>{axis.title}</h4>
          <div className="assessment-items">{axis.criteria?.map((item:Dict)=><article className="assessment-item" key={item.id}>
            <div className="assessment-item-title"><strong>{item.id} · {item.title}</strong><span className={'assessment-state '+String(item.status).toLowerCase()}>{item.status}</span></div>
            <p>{item.finding}</p><p className="muted"><strong>根拠:</strong> {item.evidence_refs?.join(', ')} ／ <strong>次の検証:</strong> {item.next_action}</p>
          </article>)}</div>
        </div>)}
        <div className="notice"><strong>診断比較の実験数と合格数を区別:</strong> Qwen/ODAの単発判定と独立ベンチマークの総合PASSは別です。
          <p className="muted">{JSON.stringify(assessment.summary_metrics?.benchmark_by_model || {})}</p>
        </div>
        <h4>Evidence register / 証拠の出所</h4>
        <div className="evidence-register">{assessment.source_register?.map((item:Dict)=><div key={item.id}><strong>{item.id} · {item.provenance}</strong><p>{item.description}</p><small>{item.source} — {item.validity}</small></div>)}</div>
        <h4>Next validation actions</h4>
        <ul className="assessment-actions">{assessment.next_actions?.map((item:Dict,i:number)=><li key={i}><strong>{item.priority}</strong> {item.action} <span className="muted">（{item.owner_role}）</span></li>)}</ul>
        <div className="button-row"><a className="download-link" href={`${BACKEND}/business-assessment/${assessment.assessment_id}/report`} target="_blank" rel="noreferrer">意思決定レポート（Markdown）</a><a className="download-link" href={`${BACKEND}/artifacts/assessments/${assessment.assessment_id}/bundle`}>レポート＋関連実験証跡 ZIP</a></div>
        <Disclosure title="独立評価・ソースハッシュ・判断結果（JSON）" data={assessment}/>
        <p className="muted">証拠IDの正確性 ≠ 証拠の妥当性 ≠ 診断の正しさ。E01–E07はこのレポート内の参照番号であり、外部資料の引用ではありません。</p>
      </section>}
    </Group>


    <Group no={10} title="00〜09 一括実行＋保存 — Full Workflow" desc="公開データモードでは、00で金融データ取得・索引化・根拠検索を自動実行し、根拠の人間レビュー後に01〜09へ進みます。05の要件改訂も別途承認が必要です。成果物は一つのZIPに保存します。">
      <div className="notice"><strong>外部データ取得失敗を合成デモとして成功扱いしません。</strong>公開データモードは00の実処理で失敗するとFAILED・PARTIAL ZIPで停止します。00の根拠選択と05の要件改訂は必ず人間が確認します。</div>
      <div className="notice"><strong>v0.21 — R1比較と診断の品質ゲート:</strong> {r1Mode==='compare'?'Qwen生成とDomain Skillを両方DEVで比較（合格候補だけHOLDOUTへ）':r1Mode==='skill_only'?'Domain Skillのみ（R1コード生成なし）':'Qwen単独でR1コード生成・修復'}。00/05の人間承認は省略しません。</div>
      <label>一括実行のモード（明示的に選択）</label>
      <div className="two-cols">
        <label className="radio"><input type="radio" name="full-run-evidence-mode" checked={evidenceMode==='public'} onChange={()=>setEvidenceMode('public')}/><span><strong>公開データ利用</strong>（推奨） — 00取得・索引化・検索 → 根拠レビュー → 01〜09</span></label>
        <label className="radio"><input type="radio" name="full-run-evidence-mode" checked={evidenceMode==='synthetic'} onChange={()=>setEvidenceMode('synthetic')}/><span><strong>合成デモのみ</strong> — 00は明示的にSKIPPED。外部データは参照しない</span></label>
      </div>
      {evidenceMode==='public' && <div className="assessment-item">
        <p><strong>00で自動実行する処理:</strong> データ取得（またはSHA256でキャッシュ検証）→ 検索インデックス更新 → 根拠検索 → 要件仮説抽出（任意）</p>
        <p className="muted">使用データセット：<strong>{evidenceDataset}</strong> / 現在の00画面で選択しているデータを使います。別途00のボタンを操作する必要はありません。</p>
        <p className="muted">検索クエリ：{evidenceQuery}</p>
        <p className="muted">Qwenの要求仮説抽出：{llmExtraction?'有効（未承認）':'無効（人間が検索結果から要求仮説を記述）'}</p>
        <p className="muted"><strong>公開資料の対象:</strong> {evidenceDataset==='insurance_claims_uk'?'保険請求の遅延・苦情（FCA/FOS）':'個人向け金融サービス。保険請求のR0/R1へは連携不可'}</p>
        <p className="muted">データセットとクエリを変更する場合は、上の00セクションで変更してください。</p>
      </div>}
      <div className="two-cols">
        <label className="radio"><input type="checkbox" checked={diagnosticRepair} onChange={e=>setDiagnosticRepair(e.target.checked)}/>04・08のLLM診断を入力事実に基づいて一度再試行。元の採点も保存</label>
        <label className="radio"><input type="checkbox" checked={diagnosticBlind} onChange={e=>setDiagnosticBlind(e.target.checked)}/>08の別ケースを初回推論だけで評価。修復・選択には使用しない</label>
      </div>
      <label htmlFor="blind-count">08f：新しいランダム化行動HOLDOUTのケース数</label>
      <select id="blind-count" value={blindCaseCount} onChange={e=>setBlindCaseCount(Number(e.target.value))}>
        <option value={2}>2（簡易検証）</option><option value={4}>4（標準）</option><option value={6}>6（広め）</option><option value={8}>8（時間・E2B使用量増加）</option>
      </select>
      <p className="muted">08fはR1のDEV選択後にだけ生成する小規模合成ケースで、固定参照・Skill・採用方式を比較します。厳密最適解の証明はソルバーがOPTIMALを返したケースに限定します。</p>
      <div className="button-row">
        {button(evidenceMode==='public'?'公開データ取得から00〜09一括実行（00レビュー・05で停止）':'合成デモ01〜09一括実行（05で停止）', 'full-run-start', async()=>{
          setExplicitReview(false);setFullRun(null);setReviewRequirement('');setSelectedEvidenceIds([]);setEvidenceReviewError('');setAcknowledgeEvidence(false);setSupportAssessment('context_only');setRequirementType('');
          const r=await call<Dict>('/full-run/start',{
            brief,seed,evidence_condition:condition,case_ids:benchmarkCases,repetitions:benchmarkRepetitions,
            evidence_mode:evidenceMode,r1_mode:r1Mode,dataset_id:evidenceDataset,evidence_query:evidenceQuery,llm_extraction:llmExtraction,
            diagnostic_repair:diagnosticRepair,diagnostic_blind_cases:diagnosticBlind,blind_case_count:blindCaseCount
          });setFullRun(r);setFullRunId(r.workflow_id);
        },brief.trim().length<20 || benchmarkCases.length===0 || (evidenceMode==='public'&&evidenceQuery.trim().length<3))}
      </div>
      <p className="muted">01の顧客ブリーフ・seed、04の模擬反例／対照条件、08の診断ケースと回数を使います。公開データを利用する場合は事業領域の一致を必須とし、00bの承認で固定合成ケースに対するKPI閾値を別途設定します。任意の顧客要件から完全なコードと評価器を自動生成する機能ではありません。</p>
      <label htmlFor="full-run-id">再表示・復旧用のWorkflow ID</label>
      <div className="button-row">
        <input id="full-run-id" value={fullRunId} placeholder="実行中/保存済みのworkflow UUID" onChange={e=>setFullRunId(e.target.value)}/>
        {button('実行状態を読み込む', 'full-run-load', async()=>{
          const r=await call<Dict>(`/full-run/${fullRunId.trim()}`);setFullRun(r);setExplicitReview(false);
        },!fullRunId.trim(),'secondary')}
      </div>
      {fullRun && <section className="assessment-report" aria-label="00〜09 一括実行状況">
        <div className="assessment-report-head"><div><span className="intro-kicker">FULL WORKFLOW / v0.21.1</span><h3>00–09 Pipeline</h3><p className="muted">Workflow ID: {fullRun.workflow_id}</p></div>
          <Status good={fullRun.status==='COMPLETE'}>{fullRun.status}</Status></div>
        {fullRun.topic_alignment && <div className="notice"><strong>公開資料と保険請求課題の対応:</strong> {fullRun.topic_alignment.status} — {fullRun.topic_alignment.reason}。一致は原文の意味的支持・因果の証明ではありません。</div>}
        {fullRun.grounded_contract_status && <p className="muted">担当者割当KPIの検証: {fullRun.grounded_contract_status}（該当要件のみ）</p>}
        {fullRun.requirement_type && <div className="notice"><strong>選択要件:</strong> {fullRun.requirement_type} ／ <strong>対応する受入試験:</strong> {fullRun.requirement_trace_status || '未実行'}<p className="muted">「進捗通知」の場合、R1担当者割当は別系統の回帰実験です。進捗通知プロトタイプの結果だけを当該要件の合成評価として扱います。</p></div>}
        <p className="muted">現在の段階: {fullRun.phase}　／　モード: {fullRun.evidence_mode==='public'?'外部データ利用':'合成デモのみ'}　／　R1: {fullRun.r1_mode || 'legacy'}　／　各工程はDockerの<code>artifacts/</code>に逐次保存します。</p>
        {fullRun.blind_optimality && <div className="notice">
          <strong>08f 独立したランダム化行動HOLDOUT：</strong>{fullRun.blind_optimality.status} / {fullRun.blind_optimality.suite_size || 0}件
          <p className="muted">証明された最適性ギャップは、ソルバーがOPTIMALを返したケースだけ計算しています。CP-SATが未導入の場合は小規模全探索に切り替わります。</p>
          <Disclosure title="08fの比較成績とソルバーの状態（根拠ZIPにも保存）" data={fullRun.blind_optimality}/>
        </div>}
        <ol className="workflow-progress">
          {fullRun.stages?.map((x:Dict)=><li key={x.name}><span className="step-label">{x.name}</span><span className={'assessment-state '+(x.status==='FAILED'?'hold':x.status==='COMPLETED'?'supported_synthetic':'demo_controlled')}>{x.status}</span><small>{x.detail}</small></li>)}
        </ol>
        {fullRun.status==='AWAITING_EVIDENCE_REVIEW' && <div className="evidence-review">
          <h4>00b — 公開根拠と要求仮説の人間レビュー</h4>
          <p>実際に取得した公開資料の断片です。<strong>一致した課題領域は証明された原因や顧客要件ではありません。</strong>この技術実証では、固定の保険案件合成データに対する明示的なKPI閾値を人間が指定します。</p>
          <div className="notice"><strong>領域ゲート:</strong> {fullRun.evidence_review?.topic_alignment?.status} — {fullRun.evidence_review?.topic_alignment?.reason}<p>許容根拠: {fullRun.evidence_review?.topic_alignment?.topic_matching_evidence_ids?.join(', ') || 'なし'}</p></div>
          <p className="muted">RAG ID: {fullRun.evidence_review?.rag_id} / Data source: {fullRun.evidence_review?.dataset_id} / Query: {fullRun.evidence_review?.query}</p>
          <div className="evidence-review-list">{fullRun.evidence_review?.evidence?.map((e:Dict)=><label key={e.evidence_id} className="evidence-select">
            <input type="checkbox" checked={selectedEvidenceIds.includes(e.evidence_id)} onChange={ev=>setSelectedEvidenceIds(prev=>ev.target.checked ? [...prev,e.evidence_id] : prev.filter(id=>id!==e.evidence_id))}/>
            <span><strong>{e.evidence_id} · {e.source_file}</strong><small>chars {e.start_char}–{e.end_char} / {e.source_type}{e.source_record_id ? ` / record: ${e.source_record_id}` : ''} / support: UNVERIFIED</small><span className="quoted-evidence">{e.quote}</span><a href={e.source_url} target="_blank" rel="noreferrer">公開出典を確認</a></span>
          </label>)}</div>
          {fullRun.evidence_review?.llm_suggestions?.length>0 && <div className="assessment-item">
            <label htmlFor="review-suggest">Qwenの未承認要求候補を参考として入力欄にコピー</label>
            <select id="review-suggest" defaultValue="" onChange={e=>{
              const item=e.target.value==='' ? null : fullRun.evidence_review.llm_suggestions[Number(e.target.value)];
              if(item) { const h=item.requirement_hypothesis || '';setReviewRequirement(h);setEvidenceReviewError('');
                const validIds = new Set((fullRun.evidence_review?.evidence || []).map((e:Dict)=>e.evidence_id));
                setSelectedEvidenceIds([...new Set<string>((item.supporting_evidence_ids || []).filter((id:string)=>validIds.has(id)))]);
                const hint=reviewFeatureHint(h);
                setRequirementType(hint==='ambiguous'?'':hint);}
            }}><option value="">手動記述／候補を選ぶ</option>{fullRun.evidence_review.llm_suggestions.map((x:Dict,i:number)=><option key={i} value={i}>{x.requirement_hypothesis?.slice(0,110)}</option>)}</select>
            <p className="muted">候補の正しさ・引用からの含意は未検証です。必ず原文を読み、必要に応じて編集してください。</p>
          </div>}
          <label htmlFor="human-evidence-requirement">人間が確認・編集した要件仮説（20文字以上、実顧客未承認）</label>
          <textarea id="human-evidence-requirement" rows={4} value={reviewRequirement} onChange={e=>{setReviewRequirement(e.target.value);setEvidenceReviewError('');}} placeholder="例：保険請求の進捗変更について契約者に通知する。顧客の正式要件としては未確認。"/>
          <label htmlFor="human-support">選択した原文が支持する範囲（人間による判断）</label>
          <select id="human-support" value={supportAssessment} onChange={e=>setSupportAssessment(e.target.value as 'supports_problem'|'context_only'|'contradicts')}>
            <option value="context_only">課題の背景説明に留まる（HOLD）</option>
            <option value="supports_problem">遅延などの問題が存在するという文脈のみ支持する（次の合成実験を許可）</option>
            <option value="contradicts">仮説に反する／不一致（HOLD）</option>
          </select>
          <label htmlFor="requirement-template">要件が対象とする機能（人間が選択・確認）</label>
          <select id="requirement-template" value={requirementType} onChange={e=>{setRequirementType(e.target.value as ReviewFeature);setEvidenceReviewError('');}}>
            <option value="">対象機能を選択してください（初期値なし）</option>
            <option value="claims_assignment">担当者割当（期限・資格・容量のR1）</option>
            <option value="claim_progress_updates">保険請求の進捗通知（別の決定的プロトタイプ）</option>
          </select>
          {reviewFeatureIssue && <div className="notice" role="status"><strong>送信前の要件チェック：</strong>{reviewFeatureIssue}</div>}
          <p className="muted">担当者割当の例：保険請求処理の期限超過を減らすため、資格と日別容量を考慮して担当者を割り当てる（原因は未確認）。</p>
          <p className="muted">進捗通知の例：保険請求の状態が変わった際、契約者へ適時に通知する（実顧客の承認は未取得）。</p>
          <div className="notice"><strong>Feature → Acceptance Test</strong><p>{requirementType==='claim_progress_updates' ?
            '進捗変更イベント→通知率・通知遅延・受信者整合性。R1の期限超過KPIはこの要件の検証に使用しません。' :
            '担当者割当→HOLDOUT期限超過・希少資格・期限優先・ストレス。進捗通知の要件はこの評価に接続できません。'}</p>
            <p className="muted">不一致の機能を選ぶとサーバーが承認を拒否します。公開資料の事実から機能が必然的に導かれると主張するものではありません。</p></div>
          {requirementType==='claims_assignment' ? <>
            <div className="two-cols">
              <div><label htmlFor="max-missed">合成HOLDOUTで許容する期限超過（未割当含む）</label>
                <input id="max-missed" type="number" min="0" max="100" value={maxTotalMissed} onChange={e=>setMaxTotalMissed(Number(e.target.value))}/></div>
              <div><label htmlFor="min-reduction">合成FIFO比で要求する改善率（%）</label>
                <input id="min-reduction" type="number" min="0" max="100" value={minReductionPct} onChange={e=>setMinReductionPct(Number(e.target.value))}/></div>
            </div>
            <label className="radio"><input type="checkbox" checked={requireBehavioral} onChange={e=>setRequireBehavioral(e.target.checked)}/>期限優先・希少資格の行動プローブを必須とする</label>
          </> : <div className="two-cols">
              <div><label htmlFor="max-notification-delay">合成通知の許容遅延（時間）</label>
                <input id="max-notification-delay" type="number" min="1" max="168" value={maxNotificationDelay} onChange={e=>setMaxNotificationDelay(Number(e.target.value))}/></div>
              <div><label htmlFor="min-notification-coverage">合成通知の最低カバレッジ（%）</label>
                <input id="min-notification-coverage" type="number" min="1" max="100" value={minNotificationCoverage} onChange={e=>setMinNotificationCoverage(Number(e.target.value))}/></div>
            </div>}
          <p className="muted">数値は合成デモ用の人間設定条件であり顧客合意KPIではありません。通知の独立プロトタイプはR1を実装変更せず、サービス統合も未実装です。</p>
          <label htmlFor="human-evidence-actor">確認担当者</label><input id="human-evidence-actor" value={evidenceActor} onChange={e=>setEvidenceActor(e.target.value)}/>
          <label htmlFor="human-evidence-rationale">選択・承認する根拠（10文字以上）</label><textarea id="human-evidence-rationale" rows={3} value={evidenceRationale} onChange={e=>setEvidenceRationale(e.target.value)}/>
          <label className="radio"><input type="checkbox" checked={acknowledgeEvidence} onChange={e=>setAcknowledgeEvidence(e.target.checked)}/>引用の実在と、証拠の妥当性・診断の正しさ・顧客の正式承認は別であることを確認した</label>
          {evidenceReviewError && <div role="alert" className="error"><strong>00b 根拠レビューの承認に失敗：</strong>{evidenceReviewError}<p>要件の機能分類、証拠ID、入力文を確認してください。入力を修正して再送信できます。</p></div>}
          <div className="button-row">
            {button('根拠を選択・仮説を承認して01〜04を実行', 'evidence-review-approve', async()=>{
              setEvidenceReviewError('');
              try {
                const r=await call<Dict>('/full-run/review-evidence',{workflow_id:fullRun.workflow_id,decision:'approved',actor:evidenceActor,rationale:evidenceRationale,
                  evidence_ids:selectedEvidenceIds,approved_requirement:reviewRequirement,
                  support_assessment:supportAssessment,max_total_missed:maxTotalMissed,
                  min_reduction_pct:minReductionPct,require_behavioral:requireBehavioral,
                  requirement_type:requirementType,max_notification_delay_hours:maxNotificationDelay,
                  min_notification_coverage_pct:minNotificationCoverage});setFullRun(r);
              } catch(e) {
                setEvidenceReviewError(e instanceof Error ? e.message : String(e));
                throw e;
              }
            },!!reviewFeatureIssue||!requirementType||!acknowledgeEvidence||fullRun.evidence_review?.topic_alignment?.status!=='TOPIC_MATCH_REVIEW_REQUIRED'||supportAssessment!=='supports_problem'||selectedEvidenceIds.length===0||!selectedEvidenceIds.some(id=>(fullRun.evidence_review?.topic_alignment?.topic_matching_evidence_ids||[]).includes(id))||reviewRequirement.trim().length<20||evidenceActor.trim().length<2||evidenceRationale.trim().length<10||(requirementType==='claims_assignment' && (!Number.isInteger(maxTotalMissed)||maxTotalMissed<0||maxTotalMissed>100||!Number.isInteger(minReductionPct)||minReductionPct<0||minReductionPct>100))||(requirementType==='claim_progress_updates' && (!Number.isInteger(maxNotificationDelay)||maxNotificationDelay<1||maxNotificationDelay>168||!Number.isInteger(minNotificationCoverage)||minNotificationCoverage<1||minNotificationCoverage>100)))}
            {button('根拠を採用せず、PARTIAL ZIPで終了', 'evidence-review-reject', async()=>{
              const r=await call<Dict>('/full-run/review-evidence',{workflow_id:fullRun.workflow_id,decision:'rejected',actor:evidenceActor,rationale:evidenceRationale});setFullRun(r);
            },evidenceActor.trim().length<2||evidenceRationale.trim().length<10,'secondary')}
          </div>
        </div>}
        {fullRun.status==='AWAITING_APPROVAL' && <div className="notice">
          <h4>05 — 人間の承認が必要です</h4>
          <p>04の診断と、元のR0実装PASSを確認してください。モデルがHOLDなら診断を修正・隠蔽せず、人間による検証継続の根拠を記録します。</p>
          <p><strong>Qwen診断:</strong> {fullRun.review?.qwen_rubric_pass?'PASS':'HOLD'}　<strong>ODA診断:</strong> {fullRun.review?.oda_rubric_pass?'PASS':'HOLD'}</p>
          {fullRun.review?.oda_failures?.length>0 && <p className="muted">ODA失敗コード: {fullRun.review.oda_failures.join(', ')}</p>}
          <div className="button-row">
            {fullRun.linked_ids?.runs && <a href={`${BACKEND}/artifacts/runs/${fullRun.linked_ids.runs}/bundle`}>R0証跡</a>}
            {fullRun.linked_ids?.proposals && <a href={`${BACKEND}/artifacts/proposals/${fullRun.linked_ids.proposals}/bundle`}>診断・提案の証跡</a>}
          </div>
          <label htmlFor="full-actor">承認担当者</label><input id="full-actor" value={actor} onChange={e=>setActor(e.target.value)}/>
          <label htmlFor="full-rationale">判断理由</label><textarea id="full-rationale" rows={3} value={rationale} onChange={e=>setRationale(e.target.value)}/>
          {!fullRun.review?.oda_rubric_pass && <>
            <label htmlFor="full-override-rationale">ODA HOLDの理由を確認したうえで継続する根拠（20文字以上）</label>
            <textarea id="full-override-rationale" rows={4} value={overrideRationale} onChange={e=>setOverrideRationale(e.target.value)}/>
            <label className="radio"><input type="checkbox" checked={acknowledgeOverride} onChange={e=>setAcknowledgeOverride(e.target.checked)}/>
              R0の独立評価PASSと模擬反例を確認しました。ODAのHOLDを保存し、人間の判断として続行します。</label>
          </>}
          <label className="radio"><input type="checkbox" checked={explicitReview} onChange={e=>setExplicitReview(e.target.checked)}/>
            提案・診断・制約を確認し、合成技術実験に限定して承認することを明示します。</label>
          <div className="button-row">
            {button('05を承認して06〜09を自動実行・ZIP保存', 'full-run-approve', async()=>{
              const r=await call<Dict>('/full-run/approve-and-continue',{workflow_id:fullRun.workflow_id,
                approval:{proposal_id:fullRun.review.proposal_id,decision:'approved',actor,rationale,
                  domain_review_override:!fullRun.review.oda_rubric_pass,
                  override_rationale:!fullRun.review.oda_rubric_pass?overrideRationale:null,
                  acknowledges_independent_r0_pass:!fullRun.review.oda_rubric_pass?acknowledgeOverride:false}});
              setFullRun(r);
            },!explicitReview || fullRun.review?.condition!=='counterexample' || !actor.trim() || rationale.trim().length<5 || (!fullRun.review?.oda_rubric_pass && (!acknowledgeOverride || overrideRationale.trim().length<20)))}
            {button('改訂を却下し、ここまでの結果をZIP保存', 'full-run-reject', async()=>{
              const r=await call<Dict>('/full-run/approve-and-continue',{workflow_id:fullRun.workflow_id,
                approval:{proposal_id:fullRun.review.proposal_id,decision:'rejected',actor,rationale}});
              setFullRun(r);
            },!actor.trim() || rationale.trim().length<5,'secondary')}
          </div>
        </div>}
        {fullRun.error && <div className="error" role="alert">処理が完了できませんでした: {fullRun.error}</div>}
        {fullRun.bundle_url && <div className="notice"><strong>証跡ZIPが保存されました。</strong> 現在の状態は{fullRun.status}です。途中停止時のZIPはPARTIALで、未完了・失敗工程をマニフェストに残します。
          <p><a className="download-link" href={fullRun.bundle_url}>00〜09の取得・根拠・実験証跡を1つのZIPでダウンロード</a></p>
        </div>}
        {fullRun.status==='RUNNING' && <p className="muted">実行中です。公開データの取得・索引化・検索はサーバー側で処理します。画面は約1.5秒ごとに保存済みの工程状況を更新します。Workflow IDで再表示できます。</p>}
      </section>}
    </Group>

    <footer><strong>評価の二層</strong>　Implementation Validity = 仕様を満たすか / Requirement Validity = 事業課題を解くか。後者は実顧客証拠が揃うまでUNVERIFIED。</footer>
  </div>;
}
