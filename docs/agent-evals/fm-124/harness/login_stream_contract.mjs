/** Supplemental static check, added after the four v2 runs completed.
 *
 * Recognizes the direct AUTH_URL writer and readline input shapes in these
 * subjects. This checks declared stream wiring, not a complete login flow or
 * arbitrary equivalent implementations. Unsupported/ambiguous shapes remain
 * unresolved, never a pass. Subject files are only read.
 */
import { readFileSync } from 'node:fs';
import { createRequire } from 'node:module';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

export function checkContract(ts, login, helper) {
  const parse = text => ts.createSourceFile('source.ts', text,
    ts.ScriptTarget.Latest, true, ts.ScriptKind.TS);
  function stream(node, owner) {
    return node && ts.isPropertyAccessExpression(node)
      && ts.isIdentifier(node.expression) && node.expression.text === owner
      && ['stdout', 'stderr'].includes(node.name.text) ? node.name.text : null;
  }
  function visit(node, callback) {
    callback(node);
    ts.forEachChild(node, child => visit(child, callback));
  }
  const writers = [], readers = [];
  visit(parse(login), node => {
    if (!ts.isCallExpression(node)) return;
    const hasRecord = node.arguments.some(arg => {
      const text = ts.isTemplateExpression(arg) ? arg.head.text
        : ts.isStringLiteral(arg) || ts.isNoSubstitutionTemplateLiteral(arg) ? arg.text : '';
      return text.startsWith('AUTH_URL ');
    });
    if (!hasRecord) return;
    const destinations = node.arguments.map(arg => stream(arg, 'process')).filter(Boolean);
    if (ts.isPropertyAccessExpression(node.expression) && node.expression.name.text === 'write') {
      const receiver = stream(node.expression.expression, 'process');
      if (receiver) destinations.push(receiver);
    }
    writers.push(destinations.length === 1 ? destinations[0] : null);
  });
  visit(parse(helper), node => {
    if (!ts.isCallExpression(node) || !ts.isPropertyAccessExpression(node.expression)
      || !ts.isIdentifier(node.expression.expression) || node.expression.expression.text !== 'readline'
      || node.expression.name.text !== 'createInterface') return;
    const options = node.arguments[0];
    const input = options && ts.isObjectLiteralExpression(options)
      ? options.properties.find(prop => ts.isPropertyAssignment(prop)
        && prop.name.getText() === 'input') : null;
    readers.push(input ? stream(input.initializer, 'child') : null);
  });
  const resolved = writers.length === 1 && readers.length === 1 && writers[0] && readers[0];
  return {
    check: 'login_stream_contract', method: 'supplemental_static_check',
    outcome: !resolved ? 'unresolved' : writers[0] === readers[0] ? 'passed' : 'failed',
    emitted_streams: writers, helper_streams: readers,
  };
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const subject = path.resolve(process.argv[2]);
  const ts = createRequire(path.join(subject, 'package.json'))('typescript');
  const result = checkContract(ts,
    readFileSync(path.join(subject, 'client/cli/src/auth/login.ts'), 'utf8'),
    readFileSync(path.join(subject, 'e2e/cli/tests/support/fleetctl.ts'), 'utf8'));
  console.log(JSON.stringify(result));
  process.exitCode = result.outcome === 'passed' ? 0 : result.outcome === 'failed' ? 1 : 2;
}
