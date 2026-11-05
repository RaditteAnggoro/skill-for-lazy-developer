import assert from 'node:assert/strict';
import { inspectWrite } from './index.js';

assert.equal(inspectWrite('mcp__engram__mem_save', { content: 'Billing uses PostgreSQL.' }), null);
assert.match(inspectWrite('mem_save', { content: 'sk-test-CANARY-7f3a9c2e1d4b8f6a' }), /sensitive|openai-style/);
assert.match(inspectWrite('mem_save', { content: 'Contact customer@example.invalid' }), /email address/);
assert.match(inspectWrite('mem_update', { replace: 'ghp_abcdefghijklmnopqrstuvwxyz012345' }), /github token/);
assert.match(inspectWrite('mem_save', { content: 'x'.repeat(4001) }), /4,000-character/);
assert.equal(inspectWrite('mem_search', { query: 'sk-test-CANARY-7f3a9c2e1d4b8f6a' }), null);
assert.match(inspectWrite('mem_save_prompt', { content: 'ordinary prompt' }), /raw prompt capture/);
console.log('guard ok');
