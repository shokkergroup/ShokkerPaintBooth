(function (global) {
  'use strict';
  var MAX_INDEX = 0xFFFFFFFF;
  function valid(v) { return Number.isInteger(v) && v >= 0 && v <= MAX_INDEX; }
  function has(z) { return !!z && Object.prototype.hasOwnProperty.call(z, 'renderSeedIndex'); }
  function maxAssigned(zones) { var max=-1; (Array.isArray(zones)?zones:[]).forEach(function(z){if(z&&valid(z.renderSeedIndex))max=Math.max(max,z.renderSeedIndex);}); return max; }
  function initialize(allZones,validZones) {
    if(!Array.isArray(allZones)||!Array.isArray(validZones))throw new TypeError('zone arrays required');
    var all=new Set(allZones),seen=new Set(),max=-1;
    if(validZones.some(function(z){return !all.has(z);}))throw new TypeError('valid zones must be drawn from all zones');
    allZones.forEach(function(z){if(!z||seen.has(z))return;seen.add(z);if(!has(z))return;if(!valid(z.renderSeedIndex)){delete z.renderSeedIndex;return;}max=Math.max(max,z.renderSeedIndex);});
    var missing=validZones.filter(function(z){return !valid(z.renderSeedIndex);});
    if(missing.length&&max+missing.length>MAX_INDEX)throw new RangeError('renderSeedIndex capacity exhausted');
    missing.forEach(function(z){z.renderSeedIndex=++max;}); return validZones.map(function(z){return z.renderSeedIndex;});
  }
  function isRenderable(z,i,suppressed,material,pixels){return !(typeof suppressed==='function'&&suppressed(z,i))&&!!z&&!z.muted&&(typeof material!=='function'||material(z))&&(z.color!==null||z.colorMode==='multi'||(typeof pixels==='function'&&pixels(z.regionMask)));}
  function prepare(allZones,suppressed,material,pixels){var v=allZones.filter(function(z,i){return isRenderable(z,i,suppressed,material,pixels);});initialize(allZones,v);return v;}
  function assignNew(allZones,fresh){if(!Array.isArray(allZones)||!fresh||allZones.indexOf(fresh)!==-1)throw new TypeError('fresh zone must be separate');var next=maxAssigned(allZones)+1;if(!valid(next))throw new RangeError('renderSeedIndex capacity exhausted');fresh.renderSeedIndex=next;return next;}
  function assignFresh(allZones,fresh,suppressed,material,pixels){prepare(allZones,suppressed,material,pixels);return assignNew(allZones,fresh);}
  function preserveStylePaste(target,copy){var had=has(target),slot=target&&target.renderSeedIndex;try{return copy();}finally{if(had)target.renderSeedIndex=slot;else delete target.renderSeedIndex;}}
  global.SPBStableZoneSeeds=Object.freeze({validIndex:valid,initialize:initialize,prepare:prepare,assignNew:assignNew,assignFresh:assignFresh,preserveStylePaste:preserveStylePaste,isRenderable:isRenderable});
})(window);
