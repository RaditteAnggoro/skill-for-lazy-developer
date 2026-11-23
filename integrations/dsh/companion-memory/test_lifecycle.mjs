import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { mkdtemp, readFile, writeFile, mkdir, chmod, realpath, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { apply } from './index.js';

const root = await mkdtemp(path.join(tmpdir(), 'dsh-lifecycle-'));
const project = path.join(root, 'project');
const bin = path.join(root, 'engram');
const log = path.join(root, 'engram.log');
const context = path.join(root, 'context.txt');
await mkdir(path.join(project, '.engram'), { recursive: true });
await writeFile(path.join(project, '.engram/config.json'), '{"project_name":"demo"}\n');
const localRoot = await realpath(project);
const fingerprint = (directory) => createHash('sha256').update(directory).digest('hex');
const memory = (projectRoot, status, body, fields = {}) => {
  const metadata = { scope: { project: 'demo' }, project_fingerprint: fingerprint(projectRoot), status, ...fields };
  return `<!-- memory-record:v1 ${JSON.stringify(metadata)} -->\n${body}`;
};
await writeFile(context, memory(localRoot, 'active', 'Previous session: RECALL-TOKEN-7319'));
await writeFile(
  bin,
  `#!/usr/bin/env python3\nimport json, os, sys\nwith open(${JSON.stringify(log)}, 'a') as f: f.write(json.dumps(sys.argv[1:]) + '\\n')\nif len(sys.argv) > 1 and sys.argv[1] == 'export':\n    with open(${JSON.stringify(context)}) as f: text = f.read()\n    records = [dict(project=sys.argv[4], scope='project', content='<!-- memory-record:v1 ' + block) for block in text.split('<!-- memory-record:v1 ')[1:]]\n    with open(sys.argv[2], 'w') as output: json.dump(dict(observations=records), output)\nelif len(sys.argv) > 1 and sys.argv[1] == 'search': print('[1] #7 (decision) — Billing database\\n    Reference #9')\nelif len(sys.argv) > 1 and sys.argv[1] == 'delete': print('Memory #' + sys.argv[2] + ' deleted')\nelif len(sys.argv) > 1 and sys.argv[1] == 'save': print('Memory saved')\n`,
);
await chmod(bin, 0o755);

const cwd = process.cwd();
process.chdir(project);
const handlers = {};
const injected = [];
const agent = {
  inject(input) { injected.push(input); },
  ctx: { on(event, handler) { handlers[event] = handler; } },
  session: {
    deriveMessages() {
      return [{
        role: 'assistant',
        content: [{ type: 'text', text: 'Implemented the lifecycle adapter and verified the flow.' }],
      }];
    },
  },
};
let created;
const ctx = {
  on(event, handler) { if (event === 'agent/created') created = handler; },
  systemPrompt: { section() {} },
  tools: { guard() {} },
};
apply(ctx, {
  engramBin: bin,
  dataDir: path.join(root, 'data'),
  statePath: path.join(root, 'opt-outs.json'),
});
await created({ agent });
assert.equal(injected.length, 0);
const enter = async () => ({ kind: 'enter', messages: [] });
const firstDecision = await handlers['agent/pre-step']({
  messages: [{ role: 'user', source: { kind: 'user' }, content: [{ type: 'text', text: 'Show what you remember' }] }],
}, enter);
assert.match(JSON.stringify(firstDecision), /RECALL-TOKEN-7319/);
assert.match(JSON.stringify(injected), /Project memory/);
await writeFile(context, [
  memory(localRoot, 'active', 'LOCAL-CURRENT'),
  memory(path.join(localRoot, '..', 'same-name-project'), 'active', 'FOREIGN-PROJECT'),
  memory(localRoot, 'stale', 'STALE-RECORD'),
  '<!-- memory-record:v1 {"status":"active"} -->\nUNBOUND-LEGACY',
].join('\n'));
await handlers['agent/pre-step']({
  messages: [{ role: 'user', source: { kind: 'user' }, content: [{ type: 'text', text: 'Show project memory again' }] }],
}, enter);
assert.match(JSON.stringify(injected.at(-1)), /LOCAL-CURRENT/);
assert.doesNotMatch(JSON.stringify(injected.at(-1)), /FOREIGN-PROJECT|STALE-RECORD|UNBOUND-LEGACY/);
await writeFile(path.join(project, 'ledger.sql'), 'SELECT 1;\n');
await writeFile(context, [
  memory(localRoot, 'active', 'Invoice UNRELATED-NOTE'),
  memory(localRoot, 'active', 'Ledger CURRENT-NOTE',
    { source_anchors: [{ path: 'ledger.sql', sha256: fingerprint('SELECT 1;\n') }] }),
  memory(localRoot, 'active', 'Ledger EXPIRED-NOTE', { review_after: '2000-01-01T00:00:00Z' }),
  memory(localRoot, 'active', 'Ledger CHANGED-SOURCE',
    { source_anchors: [{ path: 'ledger.sql', sha256: '0'.repeat(64) }] }),
].join('\n'));
await created({ agent });
const resume = await handlers['agent/pre-step']({
  messages: [{ role: 'user', source: { kind: 'user' }, content: [{ type: 'text', text: 'Lanjutkan ledger' }] }],
}, enter);
assert.match(JSON.stringify(resume), /CURRENT-NOTE/);
assert.doesNotMatch(JSON.stringify(resume), /UNRELATED-NOTE|EXPIRED-NOTE|CHANGED-SOURCE/);
await handlers['agent/pre-step']({
  messages: [{ role: 'user', source: { kind: 'user' }, content: [{ type: 'text', text: 'Remember this: Phase 3 uses bounded handoff' }] }],
}, enter);
assert.match(JSON.stringify(injected), /Saved to project memory/);
await handlers['agent/turn-stopping']({});
let saved = await readFile(log, 'utf8');
assert.match(saved, /session_summary/);
assert.match(saved, /handoff\/demo/);

await handlers['agent/pre-step']({
  messages: [{ role: 'user', source: { kind: 'user' }, content: [{ type: 'text', text: 'Forget billing database' }] }],
}, enter);
assert.match(JSON.stringify(injected), /Nothing was deleted/);
assert.doesNotMatch(await readFile(log, 'utf8'), /"delete"/);
await handlers['agent/pre-step']({
  messages: [{ role: 'user', source: { kind: 'user' }, content: [{ type: 'text', text: 'forget confirm 9' }] }],
}, enter);
assert.match(JSON.stringify(injected.at(-1)), /not among the pending matches/);
assert.doesNotMatch(await readFile(log, 'utf8'), /"delete"/);
await handlers['agent/pre-step']({
  messages: [{ role: 'user', source: { kind: 'user' }, content: [{ type: 'text', text: 'forget confirm 7' }] }],
}, enter);
assert.match(JSON.stringify(injected), /Deleted memory #7/);
assert.match(await readFile(log, 'utf8'), /"delete"/);

let testExit;
agent.session.snapshotEvents = () => [
  { type: 'tool/call', data: { callId: 'c1', name: 'bash', arguments: { command: 'pytest tests/test_x.py' } } },
  { type: 'tool/result', data: { message: { isError: false, toolCallId: 'c1', exitCode: testExit } } },
];
agent.session.deriveMessages = () => [{
  role: 'assistant',
  content: [{ type: 'text', text: 'Verification: pytest tests/test_x.py passed. Implemented the adapter and verified the flow.' }],
}];
await handlers['agent/turn-stopping']({});
const lastSaved = async () => JSON.parse((await readFile(log, 'utf8')).trim().split('\n').at(-1))[2];
assert.match(await lastSaved(), /"trust":"unverified"/);
testExit = 0;
await handlers['agent/turn-stopping']({});
assert.match(await lastSaved(), /"trust":"verified"/);

await handlers['agent/pre-step']({
  messages: [{ role: 'user', source: { kind: 'user' }, content: [{ type: 'text', text: 'Do not remember this project' }] }],
}, enter);
assert.match(JSON.stringify(injected), /Memory is disabled/);
const optOuts = JSON.parse(await readFile(path.join(root, 'opt-outs.json'), 'utf8'));
assert.equal(optOuts.projects.length, 1);
const beforeOptOutTurn = await readFile(log, 'utf8');
await handlers['agent/turn-stopping']({});
await handlers['agent/pre-step']({
  messages: [{ role: 'user', source: { kind: 'user' }, content: [{ type: 'text', text: 'Remember this: do not save' }] }],
}, enter);
assert.equal(await readFile(log, 'utf8'), beforeOptOutTurn);

const secondInjected = [];
const second = {
  inject(input) { secondInjected.push(input); },
  ctx: { on(event, handler) { handlers[event] = handler; } },
  session: { deriveMessages() { return []; } },
};
await created({ agent: second });
assert.equal(secondInjected.length, 0);

process.chdir(cwd);
await rm(root, { recursive: true, force: true });
console.log('lifecycle ok');
