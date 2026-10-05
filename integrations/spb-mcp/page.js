/* Read-only SPB inspection + ephemeral control references. No tool routing override. */
(() => {
  if (window.__spbMcp) return;
  const epoch = Math.random().toString(36).slice(2, 10);
  let serial = 0;
  const visible = el => !!(el.getClientRects().length && getComputedStyle(el).visibility !== 'hidden');
  // A layout-visible control can still sit beneath a floating panel. Report only
  // pointer reachability and the blocker tag; never serialize blocker text.
  const pointerState = el => {
    if (!visible(el) || el.matches(':disabled')) return {reachable:false, blocker:null};
    const b = el.getBoundingClientRect();
    const left = Math.max(0, b.left ?? b.x), top = Math.max(0, b.top ?? b.y);
    const right = Math.min(window.innerWidth - 1, b.right ?? (b.x + b.width));
    const bottom = Math.min(window.innerHeight - 1, b.bottom ?? (b.y + b.height));
    if (right < left || bottom < top) return {reachable:false, blocker:null};
    const points = [
      [0.5,0.5], [0.1,0.1], [0.5,0.1], [0.9,0.1],
      [0.1,0.5], [0.9,0.5], [0.1,0.9], [0.5,0.9], [0.9,0.9]
    ];
    let blocker = null;
    for (const [px,py] of points) {
      const x = left + (right - left) * px, y = top + (bottom - top) * py;
      const hit = document.elementFromPoint(x,y);
      if (hit && (hit === el || el.contains(hit))) return {reachable:true, blocker:null};
      if (!blocker && hit) blocker = hit.tagName.toLowerCase();
    }
    return {reachable:false, blocker};
  };
  const ref = el => {
    if (!el.dataset.spbMcpRef) el.dataset.spbMcpRef = epoch + '-' + (++serial);
    return el.dataset.spbMcpRef;
  };
  const text = (v, n = 160) => String(v || '').replace(/\s+/g, ' ').trim().slice(0, n);
  const bounds = el => {
    const b = el.getBoundingClientRect();
    return {x:b.x, y:b.y, width:b.width, height:b.height};
  };
  function controls({scope = 'body', search = '', offset = 0, limit = 50, hidden = false}) {
    const parent = document.querySelector(scope);
    if (!parent) throw new Error('Scope not found: ' + scope);
    const selector = 'button,input,select,textarea,summary,a[href],[role="button"],[role="tab"],[role="menuitem"],[onclick],[contenteditable="true"],canvas';
    const nodes = [...parent.querySelectorAll(selector)];
    if (parent.matches(selector)) nodes.unshift(parent);
    const matched = nodes.filter(el => {
      if (!hidden && !visible(el)) return false;
      const labels = [el.id, el.getAttribute('aria-label'), el.title, el.placeholder, el.innerText, el.name];
      return !search || labels.join(' ').toLowerCase().includes(search.toLowerCase());
    });
    return {total:matched.length, offset, next: offset + limit < matched.length ? offset + limit : null,
      controls:matched.slice(offset, offset + limit).map(el => {
        const pointer = pointerState(el);
        const out = {
        ref:ref(el), id:el.id || undefined, tag:el.tagName.toLowerCase(), type:el.type || undefined,
        role:el.getAttribute('role') || undefined,
        label:text(el.getAttribute('aria-label') || el.labels?.[0]?.innerText || el.innerText || el.title || el.placeholder || el.name),
        title:text(el.title) || undefined, visible:visible(el), disabled:!!el.disabled,
        pointerReachable:pointer.reachable, occludedBy:pointer.blocker,
        value:el.type === 'password' ? '[redacted]' : (typeof el.value === 'string' ? text(el.value) : undefined),
        checked:['checkbox','radio'].includes(el.type) ? el.checked : undefined,
        selected:el.getAttribute('aria-selected') || el.getAttribute('aria-pressed') || undefined,
        range:el.type === 'range' ? {min:el.min,max:el.max,step:el.step} : undefined,
        options:el.tagName === 'SELECT' ? [...el.options].slice(0, 40).map(o => ({value:o.value,label:text(o.label),selected:o.selected})) : undefined,
        bounds:bounds(el), pixels:el.tagName === 'CANVAS' ? {width:el.width,height:el.height} : undefined
        };
        return Object.fromEntries(Object.entries(out).filter(([k,v]) => v !== undefined && (v !== null || k === 'occludedBy')));
      })};
  }
  function state() {
    const layers = typeof _psdLayers === 'undefined' ? [] : _psdLayers;
    const zs = typeof zones === 'undefined' ? [] : zones;
    const selected = typeof getSelectedLayer === 'function' ? getSelectedLayer() : null;
    return {
      title:document.title, url:location.href, ready:document.readyState,
      tool:typeof canvasMode === 'undefined' ? null : canvasMode,
      editTarget:typeof isLayerToolbarMode === 'function' ? (isLayerToolbarMode() ? 'layer' : 'zone') : null,
      selectedLayer:selected ? {id:selected.id,name:selected.name} : null,
      selectedZone:typeof selectedZoneIndex === 'undefined' ? null : selectedZoneIndex,
      layers:layers.slice(0,100).map(l => ({id:l.id,name:l.name,visible:l.visible,locked:l.locked,opacity:l.opacity,bbox:l.bbox})),
      layerCount:layers.length,
      zones:zs.slice(0,100).map((z,index) => ({index,name:z.name,base:z.base,pattern:z.pattern,colorMode:z.colorMode,enabled:z.enabled})),
      zoneCount:zs.length,
      canvases:[...document.querySelectorAll('canvas')].filter(visible).slice(0,16).map(c => ({ref:ref(c),id:c.id,width:c.width,height:c.height,bounds:bounds(c)})),
      dialogs:[...document.querySelectorAll('[role="dialog"],dialog[open],.modal.active,.modal.show')].filter(visible).slice(0,6).map(el => ({ref:ref(el),id:el.id,text:text(el.innerText,600)})),
      renderButton:(() => {const e = document.querySelector('#btnRender'); return e ? {text:text(e.innerText),disabled:e.disabled} : null;})(),
      focus:document.activeElement ? {id:document.activeElement.id,tag:document.activeElement.tagName} : null
    };
  }
  window.__spbMcp = {controls,state};
})();
