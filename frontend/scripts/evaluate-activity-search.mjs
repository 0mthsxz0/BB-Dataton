import {readFile,writeFile,mkdir} from 'node:fs/promises';
import {performance} from 'node:perf_hooks';
import {createActivityIndex,searchActivities,isValidSelection} from '../public/activity-search.js';
const load=async file=>JSON.parse(await readFile(new URL(file,import.meta.url),'utf8'));
const catalog=await load('../public/activities.json');
const fixture=await load('../tests/fixtures/activity-evaluation.json');
const index=createActivityIndex(catalog),times=[],failures=[];
let top1=0,top3=0,invalid=0;
for(const c of fixture.cases){
  const start=performance.now();
  const r=searchActivities(index,c.description,{mode:'description',limit:3});
  times.push(performance.now()-start);
  if(r.results[0]?.activity.id===c.expectedId)top1++;
  if(r.results.some(x=>x.activity.id===c.expectedId))top3++;
  else failures.push({family:c.family,description:c.description,expectedId:c.expectedId,actual:r.results.map(x=>x.activity.id)});
  for(const x of r.results)if(!catalog.activities.some(a=>a.id===x.activity.id)||(x.subactivity&&!isValidSelection(catalog,x.activity.id,x.subactivity.id)))invalid++;
}
times.sort((a,b)=>a-b);
const report={generatedAt:new Date().toISOString(),methodology:fixture.methodology,engine:'local-rules-tfidf-v3',runtime:process.version,catalogVersion:catalog.capturedAt,count:fixture.cases.length,families:new Set(fixture.cases.map(x=>x.family)).size,top1,top3,invalid,p95Milliseconds:Number(times[Math.ceil(times.length*.95)-1].toFixed(2)),failures};
await mkdir(new URL('../docs/evidence/',import.meta.url),{recursive:true});
await writeFile(new URL('../docs/evidence/activity-evaluation.json',import.meta.url),JSON.stringify(report,null,2)+'\n');
console.log(JSON.stringify(report,null,2));
if(invalid||top1/fixture.cases.length<.9||top3/fixture.cases.length<.97)process.exitCode=1;
