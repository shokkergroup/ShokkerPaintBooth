// Same pure mutators as Apply; only preview calculation runs off the UI thread.
importScripts('adjustment-preview.js?v=spb-adjust-worker-20260907');
let source = null, mutator = null;
self.onmessage = function (event) {
    const message = event.data;
    try {
        if (message.type === 'init') {
            mutator = self.SPBAdjustmentPreview[message.mutator];
            if (typeof mutator !== 'function') throw new Error('Unknown adjustment');
            source = new Uint8ClampedArray(message.source);
            return;
        }
        if (message.type !== 'preview' || !source || !mutator) return;
        const pixels = new Uint8ClampedArray(source);
        mutator.apply(null, [pixels].concat(message.values));
        self.postMessage({ id: message.id, pixels: pixels.buffer }, [pixels.buffer]);
    } catch (error) { self.postMessage({ error: error.message }); }
};
