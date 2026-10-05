const fs = require('node:fs'), vm = require('node:vm'), assert = require('node:assert/strict');
for (const file of ['paint-booth-2-state-zones.js', 'js/zones/preview-controls.js']) {
    const source = fs.readFileSync(file, 'utf8');
    const start = source.indexOf('function openSpecMapInspector()');
    const end = source.indexOf('function closeSpecMapInspector()', start);
    const open = source.slice(start, end);
    for (const [src, complete, width, available] of [
        ['data:image/png;base64,fixture', true, 2, true],
        ['http://localhost:59879/preview/job/PREVIEW_spec.png?v=1', true, 2, true],
        ['blob:http://localhost:59879/fixture', true, 2, true],
        ['', true, 0, false], ['http://localhost/failed.png', true, 0, false],
        ['http://localhost/pending.png', false, 2, false]
    ]) {
        const elements = Object.fromEntries(['specMapInspectorModal','specMapInspectorNoData','specMapInspectorContent','specMapInspectorHint','specMapInspectorImg','specMapInspectorCanvas'].map(id => [id,{style:{}}]));
        elements.livePreviewSpecImg = {src,complete,naturalWidth:width,naturalHeight:width};
        elements.specMapInspectorImg.complete = true;
        elements.specMapInspectorImg.naturalWidth = 2;
        const doc = {getElementById:id=>elements[id]};
        let refreshed = 0;
        const c = {document:doc,doc,refreshSpecMapInspectorData:()=>refreshed++};
        vm.createContext(c);vm.runInContext(open,c);c.openSpecMapInspector();
        assert.equal(elements.specMapInspectorContent.style.display, available ? '' : 'none', file + ': ' + src);
        assert.equal(refreshed, available ? 1 : 0);
        if (available) assert.equal(elements.specMapInspectorImg.src, src);
        assert.equal(elements.specMapInspectorModal.style.display,'flex');
    }
}
console.log('Live/delegated inspector: loaded data/HTTP/blob sources accepted; empty, failed and pending images rejected.');

(async () => {
    for (const file of ['paint-booth-2-state-zones.js', 'js/zones/preview-controls.js']) {
        const source = fs.readFileSync(file, 'utf8');
        const start = source.indexOf('async function refreshSpecMapInspectorData(img)');
        const end = source.indexOf('function updateSpecMapInspectorValues()', start);
        const pending = new Map(), hint = {}, doc = {getElementById:()=>hint};
        let resets = 0, publications = 0;
        const host = {SPBSpecPngPixels:{load:src=>new Promise(resolve=>pending.set(src,resolve))},resetSpecMaterialSampleDisplay:()=>resets++};
        const c = {window:host,global:host,document:doc,doc,specMapInspectorImageData:{old:true},
            updateSpecMapInspectorValues:()=>publications++,renderSpecMapInspectorChannel:()=>{}};
        vm.createContext(c);vm.runInContext(source.slice(start,end),c);
        const img = {naturalWidth:2,currentSrc:'first.png'};
        const first = c.refreshSpecMapInspectorData(img);
        assert.equal(c.specMapInspectorImageData,null,'pending decode invalidates old sample authority');
        img.currentSrc = 'second.png';
        const second = c.refreshSpecMapInspectorData(img);
        const latest = {width:2,height:1,data:new Uint8ClampedArray([0,100,110,0,1,2,3,255])};
        pending.get('second.png')(latest);await second;
        pending.get('first.png')({old:true});await first;
        assert.equal(c.specMapInspectorImageData,latest,'late image cannot replace current raw channels');
        assert.equal(publications,1);assert.equal(resets,2);
    }
    console.log('Live/delegated raw-channel publication rejects stale decodes and resets pending samples.');
})().catch(error=>{console.error(error);process.exitCode=1});
