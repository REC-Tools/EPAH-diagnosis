/** Step 9: repeatable Chromium checks on a complete, locally generated output hub.
 * Requires an existing Playwright installation and Chromium. No browser download,
 * remote service, production publication or source/scientific approval occurs.
 */
'use strict';
const fs = require('node:fs/promises');
const path = require('node:path');
const http = require('node:http');
const crypto = require('node:crypto');
const {pathToFileURL} = require('node:url');
const {chromium} = require('playwright');

function assert(condition, message) { if (!condition) throw new Error(message); }
const digest = bytes => crypto.createHash('sha256').update(bytes).digest('hex');

async function main() {
  const [hubArg, outArg, ...extra] = process.argv.slice(2);
  assert(hubArg && outArg && !extra.length,
    'Usage: node scripts/check_v0_4_browser.js <hub> <new-QA-directory>');
  const root = await fs.realpath(hubArg), output = path.resolve(outArg);
  assert(!output.startsWith(root + path.sep) && !root.startsWith(output + path.sep) && output !== root,
    'QA results must be outside the input bundle');
  await fs.mkdir(path.dirname(output), {recursive: true});
  await fs.mkdir(output); // Fail instead of overwriting a prior QA record.
  const payload = JSON.parse(await fs.readFile(path.join(root, 'atlas/atlas_data.json'), 'utf8'));
  assert(payload.municipalities.length === 27 && payload.indicators.length === 16,
    'Browser acceptance run requires the complete 27 x 16 atlas');
  assert(payload.publication_allowed === false && payload.status === 'technical_draft_do_not_publish',
    'Only an unpublished technical atlas is supported');
  const report = {
    schema_version: '0.4-browser-qa-1', status: 'failed',
    publication_allowed: false, scientific_approval: false, visual_review_completed: false,
    synthetic_fixture: payload.synthetic_fixture === true,
    hub_manifest_sha256: digest(await fs.readFile(path.join(root, 'manifest.json'))),
    viewports: [], direct_file_navigation: 'not_tested',
    limitations: ['Sampled text contrast is not a WCAG audit.',
      'Screen reader, physical A4 print and real-source review require human checks.'],
  };
  const errors = [], externalRequests = [];
  const server = http.createServer(async (request, response) => {
    try {
      const pathname = decodeURIComponent(new URL(request.url, 'http://localhost').pathname);
      const requested = path.resolve(root, '.' + pathname, pathname.endsWith('/') ? 'index.html' : '');
      const target = await fs.realpath(requested);
      assert(target.startsWith(root + path.sep), 'Unsafe request path');
      const types = {'.html':'text/html; charset=utf-8', '.json':'application/json',
        '.svg':'image/svg+xml', '.png':'image/png', '.pdf':'application/pdf', '.csv':'text/csv'};
      response.setHeader('Content-Type', types[path.extname(target)] || 'text/plain');
      response.end(await fs.readFile(target));
    } catch { response.statusCode = 404; response.end('Not found'); }
  });
  let browser;
  try {
    await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
    const base = 'http://127.0.0.1:' + server.address().port;
    browser = await chromium.launch({executablePath: process.env.EPAH_CHROMIUM || '/usr/bin/chromium',
      headless: true, args: ['--no-sandbox']});
    report.browser_version = browser.version();
    report.playwright_version = require('playwright/package.json').version;
    const context = await browser.newContext();
    context.setDefaultTimeout(10000);
    const localFilePrefix = pathToFileURL(root + path.sep).href;
    await context.route('**/*', route => {
      const url = route.request().url();
      if (url.startsWith(base + '/') || url.startsWith(localFilePrefix)) return route.continue();
      externalRequests.push(url); return route.abort();
    });
    const page = await context.newPage();
    page.on('pageerror', error => errors.push(error.message));
    page.on('response', response => {
      if (response.status() >= 400 && !response.url().endsWith('/favicon.ico'))
        errors.push('HTTP ' + response.status() + ' for a local artifact');
    });
    try {
      await page.goto(pathToFileURL(path.join(root, 'index.html')).href);
      await page.getByRole('link', {name: "Apri l'atlante HTML", exact:true}).click();
      await page.locator('#indicator').waitFor();
      report.direct_file_navigation = 'portal_to_atlas_loaded_only';
    } catch (error) {
      if (!String(error).includes('ERR_BLOCKED_BY_ADMINISTRATOR')) throw error;
      report.direct_file_navigation = 'blocked_by_managed_browser_policy';
    }
    for (const width of [390, 768, 1280]) {
      await page.setViewportSize({width, height:900});
      await page.goto(base + '/');
      await page.screenshot({path:path.join(output, 'portal-' + width + '.png')});
      await page.getByRole('link', {name:"Apri l'atlante HTML", exact:true}).click();
      await page.locator('#indicator option').last().waitFor({state:'attached'});
      assert(await page.locator('#indicator option').count() === 16, 'Missing atlas options');
      await page.keyboard.press('Tab');
      assert(await page.locator('.skip-link').evaluate(el => el === document.activeElement),
        'The first Tab must reach the skip link');
      await page.keyboard.press('Enter');
      assert(await page.locator('#indicator').evaluate(el => el === document.activeElement),
        'Skip link must focus the indicator control');
      const focus = await page.locator('#indicator').evaluate(el => {
        const style = getComputedStyle(el);
        return {width:style.outlineWidth, style:style.outlineStyle};
      });
      assert(parseFloat(focus.width) >= 2 && focus.style !== 'none', 'Focus is not visible');
      await page.screenshot({path:path.join(output, 'keyboard-focus-' + width + '.png')});
      const search = page.locator('#search');
      const first = payload.municipalities[0];
      const normalise = name => name.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase();
      await search.fill(first.name.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase());
      const matches = payload.municipalities.filter(town => normalise(town.name).includes(normalise(first.name))).length;
      assert(await page.locator('#rows tr').count() === matches, 'Accent-insensitive search failed');
      assert((await page.locator('#rows').textContent()).includes(first.code), 'Wrong searched municipality');
      await search.fill('__nessun_comune_qa__');
      assert((await page.locator('#rows').textContent()).includes('Nessun Comune'), 'Missing empty result message');
      await page.locator('#reset-search').focus();
      await page.keyboard.press('Enter');
      assert(await search.evaluate(el => el === document.activeElement), 'Reset must focus search');
      assert(await page.locator('#rows tr').count() === 27, 'Reset lost municipalities');
      const choice = page.locator('#municipality-choice');
      await choice.focus(); await page.keyboard.press('End'); await page.keyboard.press('Enter');
      assert(await page.locator('#rows tr').count() === 1, 'Keyboard municipal selection failed');
      assert(await page.evaluate(() => document.activeElement.id.startsWith('comune-')),
        'Municipal selection must focus the selected row');
      await page.locator('#reset-search').click();
      let available = 0, absent = 0;
      for (const metric of payload.indicators) {
        await page.locator('#indicator').selectOption(metric.id);
        const cells = await page.locator('#rows tr').evaluateAll(rows =>
          rows.map(row => Array.from(row.cells, cell => cell.textContent)));
        assert(cells.length === 27, 'Municipality coverage changed');
        for (const [index, town] of payload.municipalities.entries()) {
          const observation = town.values[metric.id];
          const value = observation ? (typeof observation.value === 'number'
            ? new Intl.NumberFormat('it-IT', {maximumFractionDigits:2}).format(observation.value)
            : observation.value) + ' ' + metric.unit : 'Non acquisito';
          assert(JSON.stringify(cells[index]) === JSON.stringify(
            [town.name, town.code, observation ? observation.year : '—', value]),
            'Browser table differs from snapshot for ' + metric.id + '/' + town.code);
        }
        assert((await page.locator('#source-note').textContent()).includes(metric.source),
          'Browser source metadata differs from snapshot');
        if (metric.available) {
          available++;
          for (const img of await page.locator('#graphs img').all()) {
            await img.scrollIntoViewIfNeeded();
            await img.evaluate(el => el.decode());
            assert(await img.evaluate(el => el.naturalWidth > 0 && !!el.alt), 'Image failed or lacks alternative');
          }
          assert(await page.locator('#graphs img').count() === 2, 'Missing map/distribution');
          for (const link of await page.locator('#graphs a').all()) {
            const relative = await link.getAttribute('href');
            const response = await page.request.get(base + '/atlas/' + relative);
            assert(response.ok(), 'Dynamic chart link is broken');
          }
        } else {
          absent++;
          assert(await page.locator('#graphs img').count() === 0, 'Invented chart for missing series');
          assert(await page.locator('#pending').isVisible(), 'Missing series warning is hidden');
        }
      }
      await page.locator('#indicator').selectOption(payload.indicators[0].id);
      if (width === 1280) {
        const numeric = payload.indicators.find(metric => metric.available && metric.unit !== 'categoria');
        await page.locator('#indicator').selectOption(numeric.id);
        for (const [index, kind] of ['map','distribution'].entries()) {
          const img = page.locator('#graphs img').nth(index);
          await img.scrollIntoViewIfNeeded(); await img.evaluate(el => el.decode());
          await img.screenshot({path:path.join(output, kind + '-png.png')});
        }
        const svgPage = await context.newPage();
        await svgPage.goto(base + '/atlas/charts/' + numeric.id + '_map.svg');
        await svgPage.locator('svg').waitFor();
        await svgPage.screenshot({path:path.join(output,'map-svg.png')});
        await svgPage.close();
        const category = payload.indicators.find(metric => metric.available && metric.unit === 'categoria');
        if (category) {
          await page.locator('#indicator').selectOption(category.id);
          const img=page.locator('#graphs img').nth(1);
          await img.scrollIntoViewIfNeeded(); await img.evaluate(el => el.decode());
          await img.screenshot({path:path.join(output,'snai-counts.png')});
        }
        await page.locator('#indicator').selectOption(payload.indicators[0].id);
      }
      await page.locator('#indicator').scrollIntoViewIfNeeded();
      const contrast = await page.evaluate(() => {
        const rgb = text => text.match(/[\d.]+/g).slice(0,3).map(Number);
        const lum = color => rgb(color).map(c => {c/=255; return c<=.04045?c/12.92:((c+.055)/1.055)**2.4;})
          .reduce((total,c,i) => total+c*[.2126,.7152,.0722][i],0);
        return ['#source-note','#editorial-note','#search-help','#result-count','#reset-search'].map(selector => {
          const element=document.querySelector(selector), fg=getComputedStyle(element).color;
          let ancestor=element, bg='rgb(255, 255, 255)';
          while(ancestor) { const color=getComputedStyle(ancestor).backgroundColor;
            if(color!=='rgba(0, 0, 0, 0)' && color!=='transparent') {bg=color;break;} ancestor=ancestor.parentElement; }
          const a=lum(fg),b=lum(bg); return {selector, ratio:(Math.max(a,b)+.05)/(Math.min(a,b)+.05)};
        });
      });
      assert(contrast.every(item => item.ratio >= 4.5), 'Sampled note/control text contrast is below 4.5');
      assert(!(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth)),
        'Page has unintended horizontal overflow');
      const table = await page.locator('.tablewrap').evaluate(el => ({width:el.clientWidth, scroll:el.scrollWidth}));
      if (width === 390) assert(table.scroll > table.width, 'Mobile table scroll region is missing');
      await page.screenshot({path:path.join(output, 'atlas-' + width + '.png')});
      await page.getByRole('link', {name:/Registro delle evidenze: fonti/}).click();
      assert(await page.locator('section').count() === 16, 'Ledger lacks indicator sections');
      await page.screenshot({path:path.join(output, 'ledger-' + width + '.png')});
      report.viewports.push({width, indicators_checked:16, municipalities:27, available, absent,
        keyboard_checks:true, table_matches_snapshot:true, chart_links_checked:true,
        sampled_text_contrast:contrast.map(item => ({selector:item.selector,ratio:+item.ratio.toFixed(2)}))});
    }
    assert(!errors.length && !externalRequests.length, 'Browser errors or external dependencies: ' +
      JSON.stringify({errors, externalRequests}));
    report.status = 'technical_browser_checks_passed';
  } catch (error) {
    report.error = error.message;
    throw error;
  } finally {
    if (browser) await browser.close();
    if (server.listening) await new Promise(resolve => server.close(resolve));
    report.external_requests = externalRequests;
    report.screenshots_sha256 = {};
    for (const name of (await fs.readdir(output)).filter(name => name.endsWith('.png')).sort())
      report.screenshots_sha256[name] = digest(await fs.readFile(path.join(output,name)));
    await fs.writeFile(path.join(output, 'browser_qa.json'), JSON.stringify(report,null,2)+'\n');
    console.log(JSON.stringify(report,null,2));
  }
}
main().catch(error => {console.error(error.message); process.exitCode=1;});
