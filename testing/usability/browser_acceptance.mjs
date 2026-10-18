import { chromium } from 'playwright';
import { mkdirSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';

const base = process.argv[2];
const output = process.argv[3];
mkdirSync(output, { recursive: true });

const report = {
  status: 'failed',
  browser: 'Chromium via project-local Playwright',
  viewport_runs: [],
  personas: [],
  checks: {},
  errors: [],
};

function recordError(message) {
  report.errors.push(String(message));
}

async function login(page) {
  await page.goto(base + '/', { waitUntil: 'networkidle' });
  await page.locator('#login-username').fill('operator');
  await page.locator('#login-password').fill('operator');
  await page.getByRole('button', { name: 'Open HiveMind' }).click();
  await page.locator('#projects-view').waitFor({ state: 'visible' });
}

async function createProject(page, name) {
  await page.getByRole('button', { name: /New project/ }).click();
  await page.locator('#project-name').fill(name);
  await page.locator('#project-description-input').fill('Browser acceptance project');
  await page.locator('#project-form').getByRole('button', { name: 'Create project' }).click();
  await page.locator('#project-view').waitFor({ state: 'visible' });
}

async function seedMemoryThroughAuthenticatedApi(page, name, title, body) {
  const project = await page.evaluate(async (projectName) => {
    const response = await fetch('/api/projects');
    const payload = await response.json();
    return payload.projects.find((item) => item.name === projectName);
  }, name);
  if (!project) throw new Error('Created project was not returned by the authenticated API');
  const result = await page.evaluate(async ({ projectId, title: memoryTitle, body: memoryBody }) => {
    const response = await fetch(`/api/projects/${encodeURIComponent(projectId)}/memories`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ title: memoryTitle, body: memoryBody, tags: ['browser', 'acceptance'] }),
    });
    return { status: response.status, payload: await response.json() };
  }, { projectId: project.id, title, body });
  if (result.status !== 200 && result.status !== 201) throw new Error(`API memory seed failed: ${JSON.stringify(result)}`);
  await page.locator('#back-projects-button').click();
  await page.locator('#projects-view').waitFor({ state: 'visible' });
  await page.getByRole('button', { name: new RegExp(name) }).click();
  await page.locator('#project-view').waitFor({ state: 'visible' });
  await page.getByText('Legacy project notes and connections').click();
  await page.locator('#memory-list').getByText(title).waitFor({ state: 'visible' });
}

async function addMemory(page, title, body) {
  await page.locator('#new-memory-button').click();
  await page.locator('#memory-form').waitFor({ state: 'visible', timeout: 5000 });
  await page.locator('#memory-title').fill(title);
  await page.locator('#memory-body').fill(body);
  await page.locator('#memory-tags').fill('browser, acceptance');
  await page.locator('#memory-form').getByRole('button', { name: 'Save' }).click();
  await page.locator('#memory-list').getByText(title).waitFor({ state: 'visible' });
}

async function collectAccessibility(page) {
  return page.evaluate(() => ({
    missingLabels: [...document.querySelectorAll('input,textarea,select')]
      .filter((element) => !element.getAttribute('aria-label') && !element.id && !element.closest('label')).length,
    visibleAlerts: [...document.querySelectorAll('[role="alert"]')]
      .filter((element) => !element.hidden).map((element) => element.textContent),
    headings: [...document.querySelectorAll('h1,h2')].filter((element) => element.offsetParent).map((element) => element.textContent.trim()),
  }));
}

async function runPersona(browser, index, viewport) {
  const context = await browser.newContext({ viewport });
  const page = await context.newPage();
  const actions = [];
  page.on('pageerror', (error) => recordError(`persona ${index} pageerror: ${error}`));
  page.on('console', (message) => { if (message.type() === 'error') recordError(`persona ${index} console: ${message.text()}`); });
  try {
    await login(page); actions.push('login');
    const projectName = `Browser Persona ${index}`;
    await createProject(page, projectName); actions.push('create project');
    const hostile = `<img src=x onerror="window.__hmInjected=1"><script>window.__hmInjected=2</script>`;
    await seedMemoryThroughAuthenticatedApi(page, projectName, `Persona ${index} decision`, `Literal content: ${hostile}`); actions.push('seed memory via authenticated UI session');
    await page.locator('#memory-search').fill('decision'); actions.push('search memory');
    const content = await page.locator('#memory-list').innerText();
    const injected = await page.evaluate(() => ({
      marker: window.__hmInjected || null,
      scripts: document.querySelectorAll('#memory-list script, #memory-list img, #git-findings script, #git-findings img').length,
      body: document.body.innerHTML.includes('<script>window.__hmInjected') || document.body.innerHTML.includes('<img src=x'),
    }));
    report.personas.push({ index, viewport, actions, content_excerpt: content.slice(0, 300), injected });
    report.viewport_runs.push({ index, viewport, accessibility: await collectAccessibility(page) });
    await page.screenshot({ path: join(output, `persona-${index}-${viewport.width}x${viewport.height}.png`), fullPage: true });
    if (!content.includes(`Persona ${index} decision`)) throw new Error('Saved memory not visible in the memory list');
    if (injected.marker !== null || injected.scripts !== 0 || injected.body) throw new Error('UI injection executed or rendered as markup');
    await page.keyboard.press('Tab');
    await page.keyboard.press('Tab');
    report.personas.at(-1).keyboard_focus = await page.evaluate(() => document.activeElement?.id || document.activeElement?.textContent?.trim());
  } catch (error) {
    report.personas.push({ index, viewport, actions, error: String(error) });
    recordError(`persona ${index}: ${error}`);
  } finally {
    await context.close();
  }
}

const browser = await chromium.launch({ headless: true });
try {
  for (const [index, viewport] of [
    [1, { width: 1440, height: 900 }],
    [2, { width: 1280, height: 800 }],
    [3, { width: 1024, height: 768 }],
    [4, { width: 768, height: 1024 }],
    [5, { width: 390, height: 844 }],
  ]) await runPersona(browser, index, viewport);
  report.checks.five_simulated_personas = report.personas.length === 5 && report.personas.every((p) => !p.error);
  report.checks.xss_literal_and_no_execution = report.personas.every((p) => p.injected?.marker === null && p.injected?.scripts === 0 && !p.injected?.body);
  report.checks.responsive_viewports = report.viewport_runs.length === 5;
  report.checks.keyboard_focus_observed = report.personas.every((p) => typeof p.keyboard_focus === 'string' && p.keyboard_focus.length > 0);
  report.status = Object.values(report.checks).every(Boolean) ? 'passed' : 'failed';
} catch (error) {
  recordError(error);
} finally {
  await browser.close();
}

writeFileSync(join(output, 'report.json'), JSON.stringify(report, null, 2), 'utf-8');
console.log(JSON.stringify(report));
process.exitCode = report.status === 'passed' ? 0 : 1;
