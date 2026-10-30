const puppeteer = require('../frontend/node_modules/puppeteer-core');

async function testAssistant() {
  console.log('Launching headless Edge...');
  const browser = await puppeteer.launch({
    executablePath: 'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe',
    headless: 'new',
    args: ['--no-sandbox', '--disable-setuid-sandbox'],
  });

  const page = await browser.newPage();

  const consoleLogs = [];
  const errors = [];

  page.on('console', (msg) => {
    const text = `[BROWSER CONSOLE ${msg.type().toUpperCase()}] ${msg.text()}`;
    console.log(text);
    consoleLogs.push(text);
  });

  page.on('pageerror', (err) => {
    const text = `[PAGE ERROR] ${err.toString()}\n${err.stack}`;
    console.error(text);
    errors.push(text);
  });

  page.on('requestfailed', (req) => {
    console.warn(`[REQUEST FAILED] ${req.url()} - ${req.failure()?.errorText}`);
  });

  // Navigate to domain first to set localStorage
  console.log('Navigating to http://localhost:5173/onboarding to initialize state...');
  await page.goto('http://localhost:5173/onboarding', { waitUntil: 'networkidle2' });

  // Set active restaurant in localStorage
  await page.evaluate(() => {
    const rest = { id: 4, name: 'Chiku Da Dhaba', city: 'Chandigarh', category: 'Punjabi Dhaba' };
    const run = { id: 6, restaurant_id: 4, status: 'completed' };
    localStorage.setItem('menumind_active_restaurant', JSON.stringify(rest));
    localStorage.setItem('menumind_active_run', JSON.stringify(run));
  });

  console.log('Navigating to http://localhost:5173/assistant...');
  await page.goto('http://localhost:5173/assistant', { waitUntil: 'networkidle2' });

  await new Promise((r) => setTimeout(r, 2000));

  const bodyHtml = await page.evaluate(() => document.body.innerHTML);
  console.log('Body length:', bodyHtml.length);
  console.log('Root innerHTML preview:', bodyHtml.slice(0, 300));

  const pageText = await page.evaluate(() => document.body.innerText);
  console.log('\n=== PAGE INNER TEXT SNIPPET (First 800 chars) ===');
  console.log(pageText.slice(0, 800));

  const hasAssistantHeading = pageText.includes('AI Restaurant Consultant') || pageText.includes('MenuMind Assistant') || pageText.includes('Conversations');
  console.log('\nHas Assistant elements:', hasAssistantHeading);

  if (errors.length > 0) {
    console.error('\n=== DETECTED ERRORS ===');
    errors.forEach((e) => console.error(e));
  } else {
    console.log('\n=== NO PAGE ERRORS DETECTED ===');
  }

  await browser.close();
}

testAssistant().catch((err) => {
  console.error('Test script failed:', err);
  process.exit(1);
});
