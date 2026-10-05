/* SPB-93 owner09-08: complete Select Object → handles → Apply/Cancel.
 * Presentation routes to existing dispatch/controllers; no new pixel authority.
 */
(function () {
    'use strict';
    const bar = document.getElementById('spbTopToolbar');
    if (!bar) return;
    const button = (label, action, help) => {
        const b = document.createElement('button');
        b.type = 'button'; b.className = 'vtool-btn'; b.textContent = label;
        b.title = help || label; b.onclick = action; return b;
    };
    function selectObject() {
        if (typeof _psdLayersLoaded !== 'undefined' && _psdLayersLoaded) {
            activateLayerElementPickMode();
        } else setCanvasMode('grab-object');
    }
    window.spbSelectObject = selectObject;
    window.spbTransformObjectAt = function(layer, x, y) {
        // A connected object's bounds can use the existing sub-element
        // transform directly; no temporary Zone mask or clipboard lift.
        const member = window.SPBElementTransformState?.memberAt(layer, x, y);
        window._spbLastPickedElementBbox = member ? {...member,layerId:layer.id} : null;
        if (!member) selectConnectedLayerPixelsAtPoint(layer.id,x,y,{previewOnly:true,allowSnap:true});
        if (window._spbLastPickedElementBbox?.layerId !== layer.id) return false;
        return activateLayerTransform() === true;
    };
    const grab = document.getElementById('vtModeGrabObject');
    if (grab) {
        grab.textContent = 'Select Object'; grab.setAttribute('aria-label', 'Select Object');
        grab.title = 'Hover a number or logo; click to get move, resize and rotate handles. Finds artwork across visible layers.';
        grab.onclick = selectObject;
    }
    // The old Zone grab remains explicitly available for material selection.
    const menus = [...bar.querySelectorAll('details.spb-tb-menu')];
    const findMenu = name => menus.find(m => m.querySelector('summary')?.textContent.trim().startsWith(name));
    const transform = findMenu('Transform');
    if (transform) {
        const pop = transform.querySelector('.spb-tb-pop');
        const fit = pop.querySelector('button[onclick*="fitLayerToZoneSelection"]');
        pop.replaceChildren();
        pop.append(button('Select an object to transform', selectObject));
        pop.append(button('Free Transform · Ctrl+T', () => {
            if (typeof freeTransformState !== 'undefined' && freeTransformState) return;
            spbSmartTransform();
        }, 'Move inside the box, resize with handles, rotate outside a corner. Enter applies; Esc cancels.'));
        pop.append(button('Transform selected pixels', () => {
            if (typeof freeTransformState !== 'undefined' && freeTransformState) return;
            if (typeof setToolbarEditMode === 'function') setToolbarEditMode('layer', {preserveTool:true});
            if (!requestContextTransform('selection')) showToast('Select pixels with Rectangle, Lasso or a material mask first.', 'info');
        }));
        pop.append(button('Transform entire layer', () => {
            if (typeof freeTransformState !== 'undefined' && freeTransformState) {
                showToast('Apply or cancel this transform before choosing the entire layer.', 'info'); return;
            }
            if (typeof setToolbarEditMode === 'function') setToolbarEditMode('layer', {preserveTool:true});
            requestContextTransform('layer');
        }));
        function transformAction(action) {
            if (!(typeof freeTransformState !== 'undefined' && freeTransformState) && !spbSmartTransform()) return;
            action();
        }
        pop.append(button('Rotate 90° clockwise', () => transformAction(() => rotateActiveTransformBy(90))));
        pop.append(button('Flip horizontal', () => transformAction(() => {
            if (!flipActiveLayerTransformH()) showToast('Use the Zone placement flip controls for a material.', 'info');
        })));
        pop.append(button('Flip vertical', () => transformAction(() => {
            if (!flipActiveLayerTransformV()) showToast('Use the Zone placement flip controls for a material.', 'info');
        })));
        if (fit) pop.append(fit);
    }
    const mask = findMenu('Mask');
    const spec = findMenu('Spec Tools');
    if (mask) {
        const pop = mask.querySelector('.spb-tb-pop');
        const old = [...pop.children];
        const advanced = document.createElement('details'); advanced.className = 'spb-tool-more';
        const title = document.createElement('summary'); title.textContent = 'Refine edges & advanced masks';
        advanced.append(title);
        const advancedBody = document.createElement('div'); advancedBody.className = 'spb-tool-more-body';
        old.forEach(el => advancedBody.append(el)); advanced.append(advancedBody);
        pop.replaceChildren();
        pop.append(button('Select material area', () => setCanvasMode('grab-object'), 'Select an outlined number or logo as a Zone material mask.'));
        ['vtModeSpatialInclude','vtModeSpatialExclude','vtModeSpatialErase'].forEach((id,i) => {
            const b = advanced.querySelector('#'+id);
            if (b) { b.textContent = ['Paint area in','Exclude area','Erase mask strokes'][i]; b.setAttribute('aria-label',b.textContent); pop.append(b); }
        });
        pop.append(button('Pixel detail · 1:1', () => window.spbPixelDetail(), 'Zoom to individual pixels for precise Exclude strokes. Hold Space to pan.'));
        pop.append(advanced);
        if (spec) {
            spec.classList.remove('spb-tb-menu'); spec.classList.add('spb-tool-more');
            spec.querySelector('summary').textContent = 'Advanced spec utilities';
            spec.querySelector('summary').className = '';
            spec.querySelector('.spb-tb-pop').className = 'spb-tool-more-body';
            pop.append(spec);
        }
    }
    // One transform entry point, with original shortcut/controller retained.
    const xform = document.getElementById('vtModeLayerTransform');
    if (xform) xform.hidden = true;
    // Close the owning top-level menu after a nested command too.
    bar.addEventListener('click', e => {
        if (!e.target.closest('button')) return;
        const menu = e.target.closest('details.spb-tb-menu'); if (menu) menu.open = false;
    });
}());
