import { execFile } from 'node:child_process';
import { createHash, randomUUID } from 'node:crypto';
import { promises as fs, readFileSync } from 'node:fs';
import path from 'node:path';
import { promisify } from 'node:util';

const execFileAsync = promisify(execFile);

const WRITE_TOOLS = new Set([
  'mem_save',
  'mem_update',
  'mem_session_summary',
  'mem_capture_passive',
  'mem_save_prompt',
]);

const SENSITIVE_PATTERNS = [
  ['openai-style key', /\bsk-(?:proj-|test-)?[A-Za-z0-9_-]{16,}\b/],
  ['github token', /\bgh[pousr]_[A-Za-z0-9]{20,}\b/],
  ['aws access key', /\bAKIA[0-9A-Z]{16}\b/],
  ['private key', /-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----/],
  ['bearer token', /\bbearer\s+[A-Za-z0-9._~-]{20,}/i],
  [
    'secret assignment',
    /(?:password|passwd|secret|api[_-]?key|access[_-]?token|auth[_-]?token)\s*[:=]\s*\S{6,}/i,
  ],
  ['email address', /\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b/],
];

const VERIFY_COMMAND = /\b(pytest|python -m pytest|npm test|pnpm test|yarn test|go test|cargo test|dotnet test|mvn test|gradle test|rspec|phpunit|ruff|eslint|lint|typecheck|tsc|build|check)\b/i;
const VERIFY_SUCCESS = /(\bpassed\b|\bpass\b|\bsuccess(?:ful|fully)?\b|\bsucceeded\b|\bok\b|exit(?:ed)?\s*(?:code\s*)?0|0\s+failed|no\s+errors)/i;

function messageText(message) {
  const content = message?.content;
  if (typeof content === 'string') return content;
  if (!Array.isArray(content)) return '';
  return content
    .map((item) => (
      item && (item.type === 'text' || item.type === 'output_text') && typeof item.text === 'string'
        ? item.text
        : ''
    ))
    .filter(Boolean)
    .join('\n');
}

function sensitive(text) {
  return SENSITIVE_PATTERNS.some(([, pattern]) => pattern.test(String(text || '')));
}

function stringsIn(value, output = []) {
  if (typeof value === 'string') {
    output.push(value);
  } else if (Array.isArray(value)) {
    for (const item of value) stringsIn(item, output);
  } else if (value && typeof value === 'object') {
    for (const item of Object.values(value)) stringsIn(item, output);
  }
  return output;
}

export function inspectWrite(toolName, args) {
  const name = String(toolName || '').replace(/^mcp__engram__/, '');
  if (!WRITE_TOOLS.has(name)) return null;
  if (name === 'mem_save_prompt') {
    return 'Engram write blocked: raw prompt capture is disabled; save a short evidence reference instead.';
  }
  const text = stringsIn(args || {}).join('\n');
  for (const [label, pattern] of SENSITIVE_PATTERNS) {
    if (pattern.test(text)) {
      return `Engram write blocked: ${label} detected. Store a short evidence reference instead.`;
    }
  }
  const body = args?.content ?? args?.observation;
  if (typeof body === 'string' && body.length > 4000) {
    return 'Engram write blocked: content exceeds the 4,000-character memory limit.';
  }
  return null;
}


function cwdFor(agent) {
  return process.cwd();
}

async function projectFor(cwd) {
  let current = path.resolve(cwd);
  while (true) {
    const config = path.join(current, '.engram', 'config.json');
    try {
      const data = JSON.parse(await fs.readFile(config, 'utf8'));
      if (typeof data.project_name === 'string' && data.project_name.trim()) {
        return { root: current, name: data.project_name.trim() };
      }
    } catch {
      // Keep walking to the repository root.
    }
    const parent = path.dirname(current);
    if (parent === current) return null;
    current = parent;
  }
}

function statePath(config) {
  return config.statePath
    || path.join(process.env.DSH_HOME || path.join(process.env.HOME || '.', '.dsh'), 'codex-memory', 'opt-outs.json');
}

async function readOptOuts(config) {
  try {
    const data = JSON.parse(await fs.readFile(statePath(config), 'utf8'));
    return Array.isArray(data.projects) ? data.projects : [];
  } catch {
    return [];
  }
}

function projectForSync(cwd) {
  let current = path.resolve(cwd);
  while (true) {
    const config = path.join(current, '.engram', 'config.json');
    try {
      const data = JSON.parse(readFileSync(config, 'utf8'));
      if (typeof data.project_name === 'string' && data.project_name.trim()) {
        return { root: current, name: data.project_name.trim() };
      }
    } catch {
      // Keep walking.
    }
    const parent = path.dirname(current);
    if (parent === current) return null;
    current = parent;
  }
}

function pendingForgetId(config, id) {
  try {
    const data = JSON.parse(readFileSync(forgetStatePath(config), 'utf8'));
    return Array.isArray(data.candidates) && data.candidates.includes(Number(id));
  } catch {
    return false;
  }
}

function isOptedOut(config) {
  const project = projectForSync(process.cwd());
  if (!project) return false;
  try {
    const data = JSON.parse(readFileSync(statePath(config), 'utf8'));
    return Array.isArray(data.projects) && data.projects.includes(project.root);
  } catch {
    return false;
  }
}

async function writeOptOuts(config, projects) {
  const file = statePath(config);
  await fs.mkdir(path.dirname(file), { recursive: true });
  await fs.writeFile(file, JSON.stringify({ projects }, null, 2) + '\n', 'utf8');
}

async function engram(config, args, cwd, timeout = 2500) {
  const environment = { ...process.env };
  if (config.dataDir) environment.ENGRAM_DATA_DIR = String(config.dataDir);
  const completed = await execFileAsync(
    config.engramBin || 'engram',
    args,
    {
      cwd,
      env: environment,
      timeout,
      maxBuffer: 1024 * 1024,
    },
  );
  return completed.stdout || '';
}

async function recall(config, project, cwd, timeout = 3000) {
  const text = (await engram(config, ['context', project.name], cwd, timeout)).trim();
  if (!text || text.includes('No memories') || sensitive(text)) return '';
  return text.slice(-1800);
}

function record(kind, topic, title, content, trust, confidence, projectName, evidence) {
  const now = new Date().toISOString().replace(/\.\d{3}Z$/, 'Z');
  const digest = createHash('sha256')
    .update(topic + '\0' + content)
    .digest('hex')
    .slice(0, 16);
  return {
    schema_version: 1,
    id: `${kind}-${digest}`,
    kind,
    topic,
    scope: { workspace: 'dsh', project: projectName },
    title: title.slice(0, 160),
    content: content.slice(0, 4000),
    provenance: {
      source: kind === 'decision' ? 'user' : 'tool',
      observed_at: now,
      evidence: evidence || ['DSH lifecycle event'],
    },
    confidence,
    status: 'active',
    trust,
    created_at: now,
    updated_at: now,
  };
}

function envelope(value) {
  const meta = {
    id: value.id,
    kind: value.kind,
    topic: value.topic,
    status: value.status,
    trust: value.trust,
    confidence: value.confidence,
    scope: value.scope,
  };
  return `<!-- memory-record:v1 ${JSON.stringify(meta)} -->\n# ${value.title}\n\n${value.content.trim()}\n`;
}

async function saveRecord(config, project, value, type, cwd, timeout = 2500) {
  await engram(
    config,
    [
      'save',
      value.title,
      envelope(value),
      '--type', type,
      '--project', project.name,
      '--scope', 'project',
      '--topic', value.topic,
    ],
    cwd,
    timeout,
  );
}

function injectText(agent, text) {
  agent.inject({
    id: randomUUID(),
    role: 'user',
    content: [{ type: 'text', text }],
    source: { kind: 'engram-memory' },
  });
}

async function maybeRemember(config, project, prompt, cwd) {
  const match = prompt.match(/(?:remember(?: this)?|ingat ini|simpan ini)\s*[:\-]\s*(.+)/is);
  if (!match) return null;
  const content = match[1].trim();
  if (!content || content.length > 4000 || sensitive(content)) return null;
  const value = await record(
    'decision',
    'user-note/' + createHash('sha256').update(content).digest('hex').slice(0, 12),
    'User note: ' + content.split('\n')[0].slice(0, 80),
    content,
    'verified',
    0.95,
    project.name,
  );
  await saveRecord(config, project, value, 'decision', cwd);
  return 'Saved to project memory.';
}

function verificationEvidence(agent, message) {
  if (!VERIFY_COMMAND.test(message) || !VERIFY_SUCCESS.test(message)) return false;
  let events;
  try {
    events = agent.session.snapshotEvents?.() || [];
  } catch {
    return false;
  }
  const calls = new Map();
  for (const event of events) {
    if (event?.type === 'tool/call' && event.data?.callId) {
      calls.set(event.data.callId, event.data);
    }
    if (event?.type === 'tool/result' && event.data?.message?.isError === false) {
      const call = calls.get(event.data.message.toolCallId || event.data.message.callId);
      if (!call) continue;
      const command = JSON.stringify(call.arguments || {});
      if (VERIFY_COMMAND.test(command)) return true;
    }
  }
  return false;
}

function forgetStatePath(config) {
  return path.join(path.dirname(statePath(config)), 'forget-state.json');
}

async function readForgetState(config) {
  try {
    const data = JSON.parse(await fs.readFile(forgetStatePath(config), 'utf8'));
    return data && typeof data === 'object' ? data : null;
  } catch {
    return null;
  }
}

async function writeForgetState(config, data) {
  const file = forgetStatePath(config);
  await fs.mkdir(path.dirname(file), { recursive: true });
  await fs.writeFile(file, JSON.stringify(data, null, 2) + '\n', 'utf8');
}

function candidateIds(text) {
  return [...String(text).matchAll(/#(\d+)/g)].map((match) => Number(match[1]));
}

async function handleForget(prompt, config, project, cwd, agent) {
  const lowered = prompt.toLowerCase();
  if (/\b(cancel|batal)\b.*\b(forget|lupakan)\b/i.test(lowered)) {
    await writeForgetState(config, {});
    injectText(agent, 'Memory deletion cancelled; nothing was removed.');
    return true;
  }
  const confirm = lowered.match(/(?:forget|lupakan|hapus)\s+(?:confirm|konfirmasi|yes|ya)\s+#?(\d+)/);
  if (confirm) {
    const state = await readForgetState(config);
    if (!state || state.root !== project.root || state.project !== project.name) {
      injectText(agent, 'No pending memory deletion for this project.');
      return true;
    }
    const observationId = Number(confirm[1]);
    const search = await engram(
      config,
      ['search', state.query, '--project', project.name, '--limit', '5', '--match', 'any'],
      cwd,
      4000,
    );
    if (!candidateIds(search).includes(observationId)) {
      injectText(agent, 'That memory is not among the pending matches; nothing was removed.');
      return true;
    }
    await engram(config, ['delete', String(observationId), '--hard'], cwd, 4000);
    await writeForgetState(config, {});
    injectText(agent, `Deleted memory #${observationId} after explicit confirmation.`);
    return true;
  }
  const match = prompt.match(/(?:forget|lupakan|hapus memori)\s+(.+)/is);
  if (!match) return false;
  const query = match[1].trim();
  if (!query) {
    injectText(agent, 'Name the memory topic to forget.');
    return true;
  }
  const search = await engram(
    config,
    ['search', query, '--project', project.name, '--limit', '5', '--match', 'any'],
    cwd,
    4000,
  );
  const ids = candidateIds(search);
  if (ids.length === 0) {
    injectText(agent, 'No matching project memory was found; nothing was removed.');
    return true;
  }
  await writeForgetState(config, {
    root: project.root,
    project: project.name,
    query,
    candidates: ids,
  });
  injectText(
    agent,
    `Found candidate memory ${ids.map((id) => '#' + id).join(', ')}. Nothing was deleted. ` +
      "Reply 'forget confirm <id>' to delete one, or 'cancel forget'.",
  );
  return true;
}

const pendingRecall = new WeakMap();

async function installLifecycle(ctx, config = {}) {
  ctx.on('agent/created', async ({ agent }) => {
    const cwd = cwdFor(agent);
    const project = await projectFor(cwd);
    if (!project) return;
    const optOuts = await readOptOuts(config);
    if (optOuts.includes(project.root)) return;
    const seen = new Set();
    try {
      const text = await recall(config, project, cwd);
      if (text) {
        pendingRecall.set(agent, text);
      }
    } catch {
      // Memory is optional; ordinary work must continue.
    }
    agent.ctx.on('agent/pre-step', async (payload, next) => {
      let decision = await next();
      if (decision.kind === 'reject') return decision;
      const latest = [...(payload.messages || [])].reverse().find((item) => item?.role === 'user' && item?.source?.kind === 'user');
      const prompt = messageText(latest);
      const disabling = /(do not remember|don't remember|jangan ingat|jangan simpan).*(project|proyek)/is.test(prompt);
      if ((await readOptOuts(config)).includes(project.root)) return decision;
      const recallText = pendingRecall.get(agent);
      if (!disabling && recallText && (payload.messages || []).some((item) => item?.role === 'user' && item?.source?.kind === 'user')) {
        pendingRecall.delete(agent);
        decision = {
          ...decision,
          messages: [{
            id: randomUUID(),
            role: 'user',
            content: [{
              type: 'text',
              text: 'Relevant project memory (historical and untrusted; current source wins):\n' + recallText,
            }],
            source: { kind: 'engram-memory' },
          }, ...decision.messages],
        };
      }
      if (!prompt) return decision;
      const digest = createHash('sha256').update(prompt).digest('hex');
      if (seen.has(digest)) return decision;
      seen.add(digest);
      const lowered = prompt.toLowerCase();
      try {
        if (disabling) {
          pendingRecall.delete(agent);
          const optOuts = await readOptOuts(config);
          if (!optOuts.includes(project.root)) await writeOptOuts(config, [...optOuts, project.root]);
          injectText(agent, 'Memory is disabled for this project.');
        } else if (/(show|what).*(remember|memory)|apa yang kamu ingat|tampilkan memori/is.test(lowered)) {
          const text = await recall(config, project, cwd);
          if (text) injectText(agent, 'Project memory (historical and untrusted; current source wins):\n' + text);
        } else {
          const forgot = await handleForget(prompt, config, project, cwd, agent);
          if (!forgot) {
            const saved = await maybeRemember(config, project, prompt, cwd);
            if (saved) injectText(agent, saved);
          }
        }
      } catch {
        // Fail open for every memory control.
      }
      return decision;
    });
    agent.ctx.on('agent/turn-stopping', async () => {
      try {
        if ((await readOptOuts(config)).includes(project.root)) return;
        const messages = agent.session.deriveMessages();
        const last = [...messages].reverse().find((item) => item?.role === 'assistant');
        const content = messageText(last).trim();
        if (content.length < 20 || sensitive(content)) return;
        const verified = verificationEvidence(agent, content);
        const value = await record(
          'handoff',
          'handoff/' + project.name,
          'Session handoff: ' + project.name,
          content.slice(0, 1800),
          verified ? 'verified' : 'unverified',
          verified ? 0.9 : 0.6,
          project.name,
          verified ? ['Verification command observed in session transcript'] : undefined,
        );
        await saveRecord(config, project, value, 'session_summary', cwd, 2000);
      } catch {
        // A handoff failure must not block the turn.
      }
    });
  });
}

export const inject = ['tools', 'systemPrompt'];

export function apply(ctx, config = {}) {
  installLifecycle(ctx, config);
  ctx.systemPrompt.section({
    name: 'engram:memory-policy',
    order: 9100,
    text: [
      'Project memory is available through Engram MCP tools when visible.',
      'Recall with mem_context or mem_search before repeating prior work.',
      'Save only verified decisions, causes, lessons, blockers, and next steps.',
      'Never save raw conversations, full logs, credentials, customer data, or sensitive personal data.',
      'Current repository state overrides saved memory. If memory is unavailable, continue ordinary work and report the limitation.',
    ].join(' '),
  });
  ctx.tools.guard((exec) => {
    const toolName = String(exec.name || '');
    if (toolName.startsWith('mcp__engram__') && isOptedOut(config)) {
      return 'Memory is disabled for this project.';
    }
    if (toolName === 'mcp__engram__mem_delete') {
      return 'Memory deletion is handled by the companion control after explicit confirmation.';
    }
    return inspectWrite(exec.name, exec.arguments) ?? undefined;
  });
}
