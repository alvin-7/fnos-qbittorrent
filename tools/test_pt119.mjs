import assert from 'node:assert/strict';
import {runTorrentAction,speedValues} from '../src/pt.ts';
let calls=[];let task={hash:'a'.repeat(40),state:'forcedUP',force_start:true,progress:1};
const api=async(p,b)=>{calls.push([p,b?.toString()]);if(p.startsWith('torrents/info'))return [task];if(p==='torrents/setForceStart'){task={...task,force_start:b.get('value')==='true',state:b.get('value')==='true'?'forcedUP':'queuedUP'}}if(p==='torrents/stop')task={...task,state:'stoppedUP',force_start:false};return ''};
await runTorrentAction(api,'start',task.hash);assert.deepEqual(calls.filter(x=>!x[0].startsWith('torrents/info')).map(x=>x[0]),['torrents/setForceStart','torrents/start']);assert(calls[0][1].includes('value=false'));assert.equal(task.force_start,false);
calls=[];await runTorrentAction(api,'force',task.hash);assert.equal(task.force_start,true);assert.equal(task.state,'forcedUP');
calls=[];await runTorrentAction(api,'stop',task.hash);assert.equal(task.state,'stoppedUP');assert.equal(task.force_start,false);assert.deepEqual(calls.filter(x=>!x[0].startsWith('torrents/info')).map(x=>x[0]),['torrents/stop']);
let writes=0;await assert.rejects(runTorrentAction(async()=>{writes++;throw Error('ambiguous')},'force',task.hash));assert.equal(writes,1);
const fields={dl_limit:'0',up_limit:'25',alt_dl_limit:'10',alt_up_limit:'15',schedule_from:'08:30',schedule_to:'20:15',scheduler_days:'1',scheduler_enabled:'on'};const form=new Map(Object.entries(fields));assert.deepEqual(speedValues(form),{dl_limit:0,up_limit:25600,alt_dl_limit:10240,alt_up_limit:15360,schedule_from_hour:8,schedule_from_min:30,schedule_to_hour:20,schedule_to_min:15,scheduler_days:1,scheduler_enabled:true});
for(const bad of ['','-1','1.5','NaN','Infinity','2147483648']){assert.throws(()=>speedValues(new Map(Object.entries({...fields,up_limit:bad}))));}
for(const bad of ['','24:00','12:60','ab:cd'])assert.throws(()=>speedValues(new Map(Object.entries({...fields,schedule_from:bad}))));
console.log('pt119 unit actions/no replay/validation PASS');
