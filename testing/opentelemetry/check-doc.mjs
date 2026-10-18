// Run on stdin in /workspace so imports use the checkout's pinned dependencies.
import fs from 'node:fs';
import path from 'node:path';
import { pathToFileURL } from 'node:url';
import { load } from 'js-yaml';
import { lint } from 'markdownlint/promise';
import MarkdownIt from 'markdown-it';

const file = 'content/en/docs/contributing/development.md';
const cli = load(fs.readFileSync('.markdownlint-cli2.yaml', 'utf8'));
let config = load(fs.readFileSync('.markdownlint.yaml', 'utf8'));
let directory = '';
for (const segment of path.dirname(file).split('/')) {
  directory = path.join(directory, segment);
  for (const name of ['.markdownlint.yaml', '.markdownlint.yml']) {
    const candidate = path.join(directory, name);
    if (fs.existsSync(candidate)) {
      config = { ...config, ...load(fs.readFileSync(candidate, 'utf8')) };
    }
  }
}
const customRules = [];
for (const specifier of cli.customRules ?? []) {
  const source = specifier.startsWith('.')
    ? pathToFileURL(path.resolve(specifier)).href
    : specifier;
  const module = await import(source);
  customRules.push(...(Array.isArray(module.default) ? module.default : [module.default]));
}
const results = await lint({ files: [file], config, customRules,
  markdownItFactory: () => new MarkdownIt({ html: true }) });
if (!Object.hasOwn(results, file)) {
  throw new Error('The requested file was not linted');
}
console.log(`Direct Markdown validation: 1 file; ${results[file].length} issues; ${customRules.length} custom rules.`);
for (const issue of results[file]) {
  console.error(`${file}:${issue.lineNumber}: ${issue.ruleNames.join('/')} ${issue.errorDetail ?? ''}`);
}
process.exitCode = results[file].length ? 1 : 0;
