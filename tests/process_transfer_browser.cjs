// Optional standalone Playwright smoke test. All records are synthetic_test.
const {chromium}=require('playwright');
const fs=require('fs');
const path=require('path');
const {pathToFileURL}=require('url');
const directory=path.resolve(process.argv[2]||(()=>{throw Error('Supply fresh generated test directory');})());
(async()=>{
 const plan=JSON.parse(fs.readFileSync(path.join(directory,'plan.json'),'utf8'));
 if(plan.version!=='process-transfer-0.2'||plan.evidence_origin!=='synthetic_test')throw Error('Require0.2 synthetic_test plan');
 for(let i=1;i<=9;i++)if(fs.existsSync(path.join(directory,'export-'+i+'.json')))throw Error('Use fresh output directory');
 const browser=await chromium.launch({executablePath:process.env.CHROME_PATH||undefined,headless:true});
 const errors=[],requests=[];
 try{
  const context=await browser.newContext({acceptDownloads:true});
  const newPage=async()=>{const p=await context.newPage();p.on('pageerror',e=>errors.push(e.message));p.on('request',r=>{if(/^https?:/.test(r.url()))requests.push(r.url());});return p;};
  const cases=[];
  for(const arm of ['assistant_dependency','assistant_selection'])for(const tools of ['available','unavailable'])for(const order of ['ratings_first','forecasts_first']){
   cases.push(plan.allocations.find(a=>a.stimuli.arm===arm&&a.future_tools===tools&&a.measure_order===order));
  }
  let n=0;
  for(const a of cases){
   const page=await newPage();await page.goto(pathToFileURL(path.join(directory,a.allocation_id+'.html')).href);
   await page.locator('#next').click();if(!(await page.locator('#error').innerText()).includes('код'))throw Error('Missing code not blocked');
   await page.locator('#pid').fill('P-'+String(++n).padStart(12,'0'));await page.locator('#consent').check();await page.locator('#next').click();
   if(n===1){await page.screenshot({path:path.join(directory,'desktop.png'),fullPage:true});await page.setViewportSize({width:390,height:844});await page.screenshot({path:path.join(directory,'mobile-top.png')});if(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth))throw Error('Mobile exposure overflow');}
   await page.locator('#next').click();let forecast=0;
   for(let i=0;i<5;i++){
    if(await page.locator('#forecast').count()){
     const text=await page.locator('#screen').innerText();
     if(a.future_tools==='available'&&!text.includes('модуль доступен'))throw Error('Wrong available target');
     if(a.future_tools==='unavailable'&&!text.includes('модуль недоступен'))throw Error('Wrong unavailable target');
     await page.locator('#forecast').pressSequentially('-');await page.locator('#next').click();
     if(!(await page.locator('#error').innerText()).includes('Завершите ввод'))throw Error('Malformed number lost');
     await page.locator('#forecast').fill('101');await page.locator('#next').click();
     if(!(await page.locator('#error').innerText()).includes('0 до 100'))throw Error('Range not enforced');
     await page.locator('#forecast').fill(['0','100','','65'][forecast++]);
    }else{await page.locator('#smartness').selectOption('5');}
    await page.locator('#next').click();
   }
   await page.locator('#credit').selectOption('4');
   await page.locator('#dependency_source').selectOption(a.stimuli.assistant_operation==='dependency'?'assistant':'component');
   await page.locator('#selection_source').selectOption(a.stimuli.assistant_operation==='selection'?'assistant':'component');
   await page.locator('#allocation').selectOption('assigned');await page.locator('#tools').selectOption(a.future_tools);
   await page.locator('#interpretation').fill('Synthetic UI test only.');
   const download=page.waitForEvent('download');await page.locator('#next').click();await(await download).saveAs(path.join(directory,'export-'+n+'.json'));
   const saved=JSON.parse(fs.readFileSync(path.join(directory,'export-'+n+'.json'),'utf8'));
   if(saved.evidence_origin!=='synthetic_test'||saved.status!=='complete')throw Error('Wrong provenance/status');
   await page.close();
  }
  const a=plan.allocations.find(a=>!cases.includes(a));const page=await newPage();
  await page.goto(pathToFileURL(path.join(directory,a.allocation_id+'.html')).href);
  await page.locator('#pid').fill('P-000000000009');await page.locator('#consent').check();await page.locator('#next').click();await page.locator('#next').click();
  const download=page.waitForEvent('download');await page.locator('#partial').click();await(await download).saveAs(path.join(directory,'export-9.json'));
  if(errors.length||requests.length)throw Error(JSON.stringify({errors,requests}));
  console.log('8 complete + 1 partial synthetic exports; roles/resources/orders; endpoints/missing; mobile exposure; no network requests or JS errors.');
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
