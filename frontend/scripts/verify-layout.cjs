// v0.27.1 regression: UI section order is 10 -> finished report -> 00 -> 01.
// TypeScript is already a devDependency; no browser or external API needed.
const ts = require('typescript');
const fs = require('node:fs');
const path = require('node:path');
const assert = require('node:assert/strict');
const source = fs.readFileSync(path.resolve(__dirname, '../src/App.tsx'), 'utf8');
const ast = ts.createSourceFile('App.tsx', source, ts.ScriptTarget.Latest, true, ts.ScriptKind.TSX);
assert.equal(ast.parseDiagnostics.length, 0, 'App.tsx has TSX parse errors');
const nodeText = n => n.getText(ast);
let shell;
function seek(n) {
  if (ts.isJsxElement(n) && nodeText(n.openingElement.tagName) === 'div' && nodeText(n.openingElement.attributes).includes('app-shell')) shell=n;
  ts.forEachChild(n, seek);
}
seek(ast); assert.ok(shell, 'app-shell missing');
const rendered = [];
for (const item of shell.children) {
  if (ts.isJsxElement(item) && nodeText(item.openingElement.tagName) === 'Group') {
    const no=item.openingElement.attributes.properties.find(x=>x.name?.text==='no');
    if (no) rendered.push({kind:'group', key:nodeText(no.initializer).replace(/[^0-9]/g,''), item});
  } else if (ts.isJsxElement(item) && nodeText(item.openingElement.attributes).includes('evidence-rag-panel')) {
    rendered.push({kind:'manual', key:'00', item});
  } else if (ts.isJsxExpression(item) && nodeText(item).includes('full-run-report-placement')) {
    rendered.push({kind:'report', key:'10R', item});
    const text=nodeText(item);
    assert.ok(text.includes("['COMPLETE','PARTIAL'].includes(fullRun.status)"), 'terminal-state report guard missing');
    assert.ok(text.includes('fullRunReport.workflow_id === fullRun.workflow_id'), 'report/run identity guard missing');
    assert.ok(text.includes('fullRunReport.updated_at === fullRun.updated_at'), 'stale report guard missing');
    assert.ok(text.includes('full-run-report-reload'), 'manual retry missing');
    assert.ok(text.includes('<AdvisoryPanel'), '10R advisory panel missing');
    assert.ok(text.indexOf('<AdvisoryPanel') < text.indexOf('<WorkflowReportPanel'), 'AI proposal must render before detailed results');
  }
}
const indices=Object.fromEntries(rendered.map((x,i)=>[x.key,i]));
for (const k of ['10','10R','00','1','9']) assert.ok(k in indices, `missing section ${k}`);
assert.equal(indices['10R'],indices['10']+1,'report must be immediately after 10');
assert.equal(indices['00'],indices['10R']+1,'00 must be immediately after report');
assert.equal(indices['1'],indices['00']+1,'01 must follow 00');
assert.ok(indices['9']>indices['1'],'09 must remain after 01');
const ten=rendered[indices['10']].item;
assert.ok(!nodeText(ten).includes('<WorkflowReportPanel'), 'report must not be nested inside 10');
for (const label of ['full-run-evidence-dataset','full-run-evidence-query','full-run-brief'])
  assert.ok(nodeText(ten).includes(label), `step 10 input ${label} missing`);
console.log('PASS: top-level UI order = 10 -> 10R report -> 00 -> 01..09, terminal/read-only safeguards preserved');
