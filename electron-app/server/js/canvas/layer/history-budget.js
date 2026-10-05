(function(global) {
  'use strict';

  function sourceBytes(source) {
    if (!source) return 0;
    var width = Math.max(0, Number(source.naturalWidth || source.width) || 0);
    var height = Math.max(0, Number(source.naturalHeight || source.height) || 0);
    return width * height * 4;
  }

  function entryBytes(entry) {
    if (!entry) return 0;
    if (entry.type === 'image') return sourceBytes(entry.imgCanvas);
    if (entry.type !== 'stack' || !Array.isArray(entry.snapshot)) return 0;
    var seen = new Set();
    var total = 0;
    entry.snapshot.forEach(function(layer) {
      var source = layer && layer.img;
      if (!source || seen.has(source)) return;
      seen.add(source);
      total += sourceBytes(source);
    });
    if (entry.smartTgaFlatCanvas) total += sourceBytes(entry.smartTgaFlatCanvas);
    return total;
  }

  function stackBytes(stack, retainedSources) {
    if (!Array.isArray(stack)) return 0;
    var seen = new Set(Array.isArray(retainedSources) ? retainedSources.filter(Boolean) : []);
    var total = 0;
    function countSource(source) {
      if (!source || seen.has(source)) return;
      seen.add(source);
      total += sourceBytes(source);
    }
    stack.forEach(function(entry) {
      if (!entry) return;
      if (entry.type === 'image') {
        countSource(entry.imgCanvas);
        return;
      }
      if (entry.type !== 'stack' || !Array.isArray(entry.snapshot)) return;
      entry.snapshot.forEach(function(layer) { countSource(layer && layer.img); });
      countSource(entry.smartTgaFlatCanvas);
    });
    return total;
  }

  function trim(stack, options) {
    if (!Array.isArray(stack)) return { evicted: 0, bytes: 0, entries: 0 };
    options = options || {};
    var minEntries = Math.max(0, Math.floor(Number(options.minEntries) || 0));
    var maxEntries = Math.max(minEntries, Math.floor(Number(options.maxEntries) || minEntries));
    var byteBudget = Math.max(0, Number(options.byteBudget) || 0);
    var retainedSources = Array.isArray(options.retainedSources) ? options.retainedSources : [];
    var bytes = stackBytes(stack, retainedSources);
    var evicted = 0;
    while (stack.length > maxEntries || (stack.length > minEntries && byteBudget > 0 && bytes > byteBudget)) {
      var removed = stack.shift();
      bytes = stackBytes(stack, retainedSources);
      evicted += 1;
      if (typeof options.onEvict === 'function') options.onEvict(removed);
    }
    return { evicted: evicted, bytes: bytes, entries: stack.length };
  }

  global.SPBLayerHistoryBudget = {
    sourceBytes: sourceBytes,
    entryBytes: entryBytes,
    stackBytes: stackBytes,
    trim: trim
  };
})(typeof window !== 'undefined' ? window : globalThis);
