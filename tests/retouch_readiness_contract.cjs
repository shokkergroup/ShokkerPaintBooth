// Execute real dispatch + menu controller against failed and successful recovery.
const assert = require('node:assert/strict');
const vm = require('node:vm');
const fs = require('node:fs');
let cases = 0;
function fixture({editable = true, locked = false, mode = 'zone', create = true, activate = true} = {}) {
    let layer = {id:'original', img:{}, locked};
    let adds = 0, changes = 0;
    const nodes = Object.fromEntries(['spbRetouchMenu','spbRetouchGate','spbRetouchGateWhy'].map(id => [id, {
        style:{}, open:true, textContent:'', classList:{toggle(){}}
    }]));
    const ctx = {console, toolbarEditMode:mode, canvasMode:'eyedropper',
        document:{readyState:'complete', getElementById:id=>nodes[id]},
        localStorage:{getItem(){return null;},setItem(){}},
        getSelectedLayer:()=>layer, getSelectedEditableLayer:()=>editable && !layer.locked ? layer : null,
        addBlankLayer(){adds++; if (!create) return; editable=true; return layer={id:'blank',img:{},locked:false};},
        setCanvasMode(tool){changes++; if (activate) {ctx.alignToolbarModeForToolActivation(tool); ctx.canvasMode=tool;}},
        showToast(message,error){ctx.toast={message,error};}
    };
    ctx.window=ctx; vm.createContext(ctx);
    for (const file of ['dispatch','retouch-readiness']) vm.runInContext(fs.readFileSync(`js/canvas/${file}.js`,'utf8'),ctx);
    ctx.toolbarEditMode=mode; // Model an already-loaded document after dispatch boot.
    return {ctx,nodes, counts:()=>[adds,changes]};
}
for (const mode of ['zone','layer']) {
    const f=fixture({mode}); f.ctx.spbUpdateRetouchGate();
    assert.equal(f.ctx.spbRetouchGateState().ok,true);
    assert.equal(f.nodes.spbRetouchGate.style.display,'none');
    assert.equal(f.ctx.toolbarEditMode,mode); assert.deepEqual(f.counts(),[0,0]); cases++;
}
{
    const f=fixture({locked:true}); f.ctx.spbUpdateRetouchGate();
    assert.match(f.nodes.spbRetouchGateWhy.textContent,/locked/);
    assert.match(f.nodes.spbRetouchGateWhy.textContent,/no pixels/);
    assert.equal(f.ctx.getSelectedLayer().locked,true); assert.deepEqual(f.counts(),[0,0]); cases++;
}
for (const opts of [{editable:false,create:false},{editable:false,activate:false}]) {
    const f=fixture(opts); assert.equal(f.ctx.spbRetouchGateFix(),false);
    assert.equal(f.ctx.toast.error,true); assert.doesNotMatch(f.ctx.toast.message,/ready on/);
    assert.equal(f.nodes.spbRetouchMenu.open,true); cases++;
}
{
    const f=fixture({editable:false}); assert.equal(f.ctx.spbRetouchGateFix(),true);
    assert.equal(f.ctx.canvasMode,'colorbrush'); assert.equal(f.ctx.toolbarEditMode,'layer');
    assert.deepEqual(f.counts(),[1,1]); assert.equal(f.ctx.toast.error,false);
    assert.equal(f.nodes.spbRetouchMenu.open,false); cases++;
}
console.log(`${cases} Retouch readiness scenarios passed`);
