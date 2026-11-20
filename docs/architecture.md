# v0.6 Architecture

```mermaid
flowchart TD
  A[顧客課題・初期価値仮説] --> B[要件ドラフト・人間による確認]
  B --> SD[サービス設計JSON: ユースケース・制約・代替案]
  SD --> C[FastAPIオーケストレーター / Qwenコード生成]
  C <--> D[Mac Studio上のOllama / Metal + Qwen3-Coder]
  C --> E[DEV seed dataset]
  E --> F[E2B: 静的Greedyと厳密DP]
  E --> G[E2B: Qwen生成コード]
  F --> H[FastAPI独立評価器]
  G --> H
  H --> I{DEV判定}
  I -->|Functional NO-GO| J[1回目:構造化エラー / 2回目:不変条件 + ASTヒント]
  I -->|Quality HOLD| K[集計代理効用・しきい値をQwenへ]
  J --> L[2回目は関数スコープのASTパッチ / 新E2B Sandbox]
  K --> L
  L --> G
  I -->|CONDITIONAL GO / 試行上限| V{機能合格候補が存在?}
  V -->|No| X[採用なし / NO-GO / HOLDOUTスキップ]
  V -->|Yes| M[機能合格の最良DEV候補を選択]
  M --> N[未使用HOLDOUT seed]
  X --> R
  N --> O[E2B: 3方式の1回限りの最終評価]
  O --> P[独立Functional / Technology Gate]
  P --> Q[学習計画の比較例]
  P --> R[Markdown/JSON+試行ログ]
  Q --> S[人間の事業・技術判断]
  R --> S
  S --> RA[二軸判定: 実装の正しさ / 要件妥当性]
  CE[実顧客の証拠と出典・人間の確認] --> RA
  RA --> RR{要件を改訂する必要がある?}
  RR -->|提案のみ / 明示的に採用| B
  RR -->|未検証| CE
```

## Isolation

- APIキーはFastAPIコンテナ側の環境変数のみで利用。E2B Sandboxへは生成コード・合成データだけを渡す。
- E2Bの各候補・改訂は独立したSandbox。開発用seedは同じ候補Sandboxで逐次実行し、各seedの出力ファイルを削除してから開始。
- 評価器はFastAPI側でLLMから独立。生成コード内のコメント・説明文を採否判定の根拠としない。
- DEV/HOLDOUTの境界はFastAPI側のオーケストレーションで強制。Qwenの修正コールバックが見るのはDEVのエラーと集計指標だけ。有効なDEV候補がない場合はHOLDOUTデータを生成せず、E2Bも呼び出さない。
- 静的AST診断はヒューリスティックな可能性の指摘であり、決定的な不具合の証明ではない。実際の採否は独立評価器によるテストでのみ判断。
- DEVスコアで候補を選ぶため、選択バイアスは存在する。HOLDOUTも同じ合成分布であり、実業務の性能の証拠ではない。

## External vs internal port

`compose.yaml` は `127.0.0.1:${API_PORT:-18000}:8000` を維持し、APIプロキシはDocker内`api:8000`を利用。Viteは5173番。

## Product positioning

新規事業を担当する人の初期技術検証を補佐する架空デモ。コードの安全な実行、監査可能な修正、技術選定の比較証拠を出すことが目的で、実在のSun Asterisk案件の実装物ではない。

## Requirement-level outer loop

- コードの内側ループ（機能NO-GO・品質HOLD）とは独立して、**要件の妥当性**を検証する。
- Qwenの外側ループへ渡すのはDEVの集計結果・診断と人間が提示した顧客証拠のみ。HOLDOUTを戻さない。
- 要件の`AC-01`などに紐づく顧客証拠を出典情報とともに保持。`synthetic`は要件の成立性を示す証拠に使わない。
- 要件改訂案は人間の承認待ちとし、元の要件ファイルを上書きしない。人間が受け入れたときのみ新しいrevisionとして再設計・再実験。
- データセットの最終評価はrevごとにseedを分離する。ただし反復実験で見たHOLDOUTを使って人間が要件を修正すれば、統計的には間接的な選択バイアスが残る。重要な最終主張には別途固定・完全秘匿の外部評価セットが必要。
- AIが提案したサービス設計が元の要件を充足しているという厳密な証明は**未実装**。要件と実装I/Oの固定評価は教育SaaSのみ。
