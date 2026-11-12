// Optional UI smoke test; synthetic fixtures only. See pilot/process_transfer/README.md.
const {chromium}=require('playwright');
const fs=require('fs');
const path=require('path');
const {pathToFileURL}=require('url');
const directory=path.resolve(process.argv[2] || (()=>{throw Error('Supply fresh generated test directory');})());
(async()=>{
 const browser=await chromium.launch({executablePath:process.env.CHROME_PATH||undefined,headless:true});
 const context=await browser.newContext({acceptDownloads:true});
 const errors=[],requests=[];const plan=JSON.parse(fs.readFileSync(path.join(directory,'plan.json'),'utf8'));
 if(plan.evidence_origin!=='synthetic_test')throw Error('Browser tests require synthetic_test plan');
 for(let i=1;i<=5;i++)if(fs.existsSync(path.join(directory,'export-'+i+'.json')))throw Error('Use fresh output directory; do not overwrite exports');
 const cases=[];for(const arm of ['derived','supplied'])for(const order of ['ratings_first','forecasts_first'])cases.push(plan.allocations.find(a=>a.stimuli.arm===arm&&a.measure_order===order));
 let n=0;
 for(const a of cases){
  const page=await context.newPage();page.on('pageerror',e=>errors.push(e.message));page.on('request',r=>{if(/^https?:/.test(r.url()))requests.push(r.url());});
  await page.goto(pathToFileURL(path.join(directory,a.allocation_id+'.html')).href);
  await page.locator('#next').click();if(!(await page.locator('#error').innerText()).includes('код'))throw Error('Missing code did not block');
  await page.locator('#pid').fill('P-'+String(++n).padStart(12,'0'));await page.locator('#consent').check();await page.locator('#next').click();
  if(n===1){await page.screenshot({path:path.join(directory,'desktop.png'),fullPage:true});await page.setViewportSize({width:390,height:844});await page.screenshot({path:path.join(directory,'mobile-top.png')});if(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth))throw Error('Mobile overflow');}
  await page.locator('#next').click();
  for(let i=0;i<5;i++){
   if(await page.locator('#forecast').count()){
    await page.locator('#forecast').pressSequentially('-');await page.locator('#next').click();if(!(await page.locator('#error').innerText()).includes('Завершите ввод'))throw Error('Malformed value silently lost');await page.locator('#forecast').fill('101');await page.locator('#next').click();if(!(await page.locator('#error').innerText()).includes('0 до 100'))throw Error('Range not enforced');
    await page.locator('#forecast').fill(i===0?'':'65');
   }else await page.locator('#smartness').selectOption('5');
   await page.locator('#next').click();
  }
  await page.locator('#source').selectOption(a.stimuli.arm==='derived'?'assistant':'component');await page.locator('#tools').selectOption('unavailable');
  const download=page.waitForEvent('download');await page.locator('#next').click();await(await download).saveAs(path.join(directory,'export-'+n+'.json'));
  await page.close();
 }
 const a=plan.allocations.find(a=>!cases.includes(a));const page=await context.newPage();
 await page.goto(pathToFileURL(path.join(directory,a.allocation_id+'.html')).href);await page.locator('#pid').fill('P-000000000005');await page.locator('#consent').check();await page.locator('#next').click();await page.locator('#next').click();
 const download=page.waitForEvent('download');await page.locator('#partial').click();await(await download).saveAs(path.join(directory,'export-5.json'));
 await browser.close();if(errors.length||requests.length)throw Error(JSON.stringify({errors,requests}));console.log('4 complete + 1 partial synthetic UI exports; both arms/orders; mobile no overflow; no network requests or JS errors.');
})();
