/* Real local Phaser/Pixi playback check. No npm install or external requests. */
'use strict';
const fs=require('fs'),path=require('path'),http=require('http'),crypto=require('crypto');
const [rootArg,pwModule,chromium,outputArg]=process.argv.slice(2);
if(!rootArg||!pwModule||!chromium){console.error('node check_game_browser.js DEMO/phaser-demo PLAYWRIGHT_MODULE CHROMIUM [REPORT]');process.exit(2);}
const root=path.resolve(rootArg),reportFile=path.resolve(outputArg||path.join(root,'browser-load.json'));
const required=['phaser-3.90.0.min.js','pixi-8.6.6.min.js'];
const missing=required.filter(f=>!fs.existsSync(path.join(root,'vendor',f)));
if(missing.length===required.length){fs.writeFileSync(reportFile,JSON.stringify({engine_load:'untested',missing_local_runtimes:missing},null,2));console.error('Missing pinned local runtimes: '+missing.join(', '));process.exit(2);}
const playwright=require(path.resolve(pwModule));
const mime={'.html':'text/html','.js':'text/javascript','.json':'application/json','.png':'image/png','.gif':'image/gif'};
const server=http.createServer((req,res)=>{
 try{
  const url=new URL(req.url,'http://localhost');
  if(url.pathname==='/favicon.ico'){res.writeHead(204);res.end();return;}
  const requested=path.resolve(root,'.'+decodeURIComponent(url.pathname==='/'?'/index.html':url.pathname));
  if(!requested.startsWith(root+path.sep)){res.writeHead(403);res.end();return;}
  const real=fs.realpathSync.native(requested);if(!real.startsWith(fs.realpathSync.native(root)+path.sep)){res.writeHead(403);res.end();return;}
  res.writeHead(200,{'Content-Type':mime[path.extname(real)]||'application/octet-stream'});res.end(fs.readFileSync(real));
 }catch(e){res.writeHead(404);res.end('Not found');}
});
(async()=>{
 await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
 const origin='http://127.0.0.1:'+server.address().port;
 const browser=await playwright.chromium.launch({executablePath:path.resolve(chromium),headless:true,args:['--no-sandbox','--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader']});
 const results={};
 try{
  for(const [engine,url,version] of [['phaser-hash','index.html','3.90.0'],['phaser-array','index.html?format=phaser-array','3.90.0'],['pixi','pixi.html','8.6.6']]){
   if(missing.includes(engine==='pixi'?required[1]:required[0])){results[engine]={engine_load:'untested',reason:'Missing pinned local runtime'};continue;}
   const page=await browser.newPage();const errors=[];
   page.on('pageerror',e=>errors.push(String(e)));page.on('console',m=>{if(m.type()==='error')errors.push(m.text());});
   await page.route('**/*',route=>{if(!route.request().url().startsWith(origin+'/'))return route.abort();return route.continue();});
   await page.goto(origin+'/'+url);
   try{await page.waitForFunction(()=>window.S14&&window.S14.done,{},{timeout:15000});}catch(e){errors.push(String(e));}
   const actual=await page.evaluate(()=>({result:window.S14||{frames:{},events:[],errors:['No runtime state']},version:typeof Phaser!=='undefined'?Phaser.VERSION:typeof PIXI!=='undefined'?PIXI.VERSION:'missing'}));
   const states=JSON.parse(fs.readFileSync(path.join(root,'states.json'),'utf8'));errors.push(...actual.result.errors);
   if(actual.version!==version)errors.push('Unexpected runtime version '+actual.version);
   for(const [name,state] of Object.entries(states)){
    const seen=new Set(actual.result.frames[name]||[]);if(seen.size!==state.frames.length)errors.push(name+': did not observe every frame');
    for(const event of state.events)if(!actual.result.events.some(e=>e.state===name&&e.name===event.name&&e.frame===event.frame))errors.push(name+': missing/wrong event '+event.name);
   }
   await page.screenshot({path:path.join(root,engine+'-loaded.png')});
   results[engine]={engine_load:errors.length?'failed':'tested:'+version,errors,frames:actual.result.frames,events:actual.result.events};await page.close();
  }
 }finally{await browser.close();}
 results.runtime_sha256=Object.fromEntries(required.filter(f=>!missing.includes(f)).map(f=>[f,crypto.createHash('sha256').update(fs.readFileSync(path.join(root,'vendor',f))).digest('hex')]));
 fs.writeFileSync(reportFile,JSON.stringify(results,null,2));
 if(Object.values(results).some(r=>r.engine_load==='failed'))process.exitCode=1;
} )().catch(e=>{fs.writeFileSync(reportFile,JSON.stringify({engine_load:'untested',error:String(e)},null,2));console.error(e);process.exitCode=2;}).finally(()=>server.close());
