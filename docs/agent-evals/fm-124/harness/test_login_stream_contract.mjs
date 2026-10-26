import assert from 'node:assert/strict';
import { createRequire } from 'node:module';
import path from 'node:path';
import test from 'node:test';

import { checkContract } from './login_stream_contract.mjs';

const ts = createRequire(path.resolve(process.env.SUBJECT || '.', 'package.json'))('typescript');
const emit = 'await writeText(process.stderr, `AUTH_URL ${url}\\n`);';
const read = stream => `readline.createInterface({input: child.${stream}});`;

test('matching direct stream arguments pass and mismatches fail', () => {
  assert.equal(checkContract(ts, emit, read('stderr')).outcome, 'passed');
  assert.equal(checkContract(ts, emit, read('stdout')).outcome, 'failed');
  assert.equal(checkContract(ts,
    'await writeOutput(`AUTH_URL ${url}`, process.stderr);', read('stderr')).outcome, 'passed');
  assert.equal(checkContract(ts,
    'process.stdout.write(`AUTH_URL ${url}`);', read('stdout')).outcome, 'passed');
});

test('comments do not count as stream wiring', () => {
  assert.equal(checkContract(ts, '// ' + emit, read('stdout')).outcome, 'unresolved');
  assert.equal(checkContract(ts, emit, '// ' + read('stderr')).outcome, 'unresolved');
});

test('unsupported indirect wiring and ambiguous readers stay unresolved', () => {
  assert.equal(checkContract(ts, 'await writeText(destination, `AUTH_URL ${url}`);',
    read('stderr')).outcome, 'unresolved');
  assert.equal(checkContract(ts, emit, read('stdout') + read('stderr')).outcome, 'unresolved');
});
