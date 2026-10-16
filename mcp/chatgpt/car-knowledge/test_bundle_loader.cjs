'use strict';
const fs=require('node:fs'),path=require('node:path'),os=require('node:os'),crypto=require('node:crypto'),assert=require('node:assert/strict'),K=require('./lookup.cjs');
const dir=fs.mkdtempSync(path.join(os.tmpdir(),'spb-car-bundle-'));
const raw=Buffer.from('{"cars":[],"test":true}\n');
try{
 fs.writeFileSync(path.join(dir,'knowledge.json'),raw);
 assert.equal(K.load(dir),null,'Missing manifest cannot establish a complete generation');
 fs.writeFileSync(path.join(dir,'manifest.json'),JSON.stringify({schema:'spb-car-build/1',outputs:{'knowledge.json':crypto.createHash('sha256').update(raw).digest('hex')}}));
 assert.equal(K.load(dir).test,true);
 fs.writeFileSync(path.join(dir,'knowledge.json'),'{"different":true}');
 assert.equal(K.load(dir),null,'Mixed generations fail closed');
 fs.writeFileSync(path.join(dir,'manifest.json'),'corrupt');assert.equal(K.load(dir),null);
 console.log('PASS bundle loader accepts complete generations and rejects missing, corrupt or mixed builds');
}finally{
 for(const name of ['knowledge.json','manifest.json'])fs.unlinkSync(path.join(dir,name));
 fs.rmdirSync(dir);
}
