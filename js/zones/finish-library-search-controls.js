(function(global) {
  'use strict';

  var FINISH_LIBRARY_SEARCH_ALIASES = {
    old: ['weathered', 'aged', 'patina', 'rust', 'worn', 'vintage'],
    rust: ['rust', 'oxidized', 'patina', 'weathered', 'corrosion'],
    weather: ['weather', 'weathered', 'aged', 'storm', 'dust', 'spray', 'sun', 'salt'],
    weathered: ['old', 'aged', 'weather', 'rust', 'patina', 'worn', 'oxidized'],
    chrome: ['chrome', 'mirror', 'reflective', 'polished'],
    flake: ['flake', 'sparkle', 'metallic', 'prizm', 'glitter'],
    carbon: ['carbon', 'composite', 'weave', 'forged'],
    mexico: ['mexico', 'mexican', 'viva', 'talavera', 'luchador', 'aztec'],
    sun: ['sun', 'solar', 'rising', 'flare', 'sunburst'],
    ocean: ['ocean', 'wave', 'tide', 'sea', 'marine'],
    matte: ['matte', 'flat', 'satin', 'low gloss'],
    gloss: ['gloss', 'wet', 'clearcoat', 'shine'],
    metal: ['metal', 'metallic', 'chrome', 'brushed', 'machined', 'forged'],
    pearl: ['pearl', 'pearlescent', 'tri coat', 'mica'],
    horror: ['horror', 'gothic', 'dark', 'graveyard', 'reaper', 'nightmare', 'cursed'],
    vision: ['vision', 'optical', 'illusion', 'depth', 'spectral', 'phantom'],
    brushed: ['brushed', 'machined', 'aniso', 'grain', 'polished', 'guilloche'],
    sponsor: ['sponsor safe', 'text safe', 'readability', 'text friendly', 'clean'],
    safe: ['sponsor safe', 'text safe', 'readability', 'text friendly', 'clean'],
    spec: ['spec', 'metallic', 'roughness', 'clearcoat', 'm r cc', 'rgb'],
    premium: ['showcase', 'hero', 'premium', 'featured', 'pro'],
    subtle: ['subtle', 'satin', 'matte', 'low gloss', 'balanced'],
    wild: ['wild', 'bold', 'aggressive', 'neon', 'plasma', 'holographic'],
    'color-shift': ['color shift', 'colorshift', 'chameleon', 'prism', 'prizm', 'holographic', 'iridescent'],
    colorshift: ['color shift', 'chameleon', 'prism', 'prizm', 'holographic', 'iridescent']
  };

  function _smartSearchTokens(query) {
    return String(query || '')
      .toLowerCase()
      .replace(/[,\t\r\n]+/g, ' ')
      .split(/\s+/)
      .map(function(word) { return word.replace(/^#+/, '').trim(); })
      .filter(Boolean);
  }

  function _smartSearchAliasesForWord(word) {
    var clean = String(word || '').toLowerCase().replace(/^#+/, '');
    var aliases = (FINISH_LIBRARY_SEARCH_ALIASES[clean] || []).slice();
    if (clean.indexOf('-') >= 0) {
      aliases.push(clean.replace(/-/g, ' '), clean.replace(/-/g, ''));
    }
    return aliases;
  }

  function _smartSearchWordMatches(hay, word, finishId) {
    var clean = String(word || '').toLowerCase().replace(/^#+/, '');
    var searchKeywords = global.SEARCH_KEYWORDS || {};
    if (!clean) return true;
    if (hay.indexOf(clean) >= 0) return true;
    var aliases = _smartSearchAliasesForWord(clean);
    if (aliases.some(function(alias) { return hay.indexOf(String(alias).toLowerCase()) >= 0; })) return true;
    if (searchKeywords[clean] && finishId && searchKeywords[clean].indexOf(finishId) >= 0) return true;
    if (clean.indexOf('-') >= 0) {
      return clean.split('-').filter(Boolean).every(function(part) {
        return _smartSearchWordMatches(hay, part, finishId);
      });
    }
    return false;
  }

  function _smartSearchScore(hay, query, finishId, labelText) {
    var words = _smartSearchTokens(query);
    var searchKeywords = global.SEARCH_KEYWORDS || {};
    if (!words.length) return 0;
    var id = String(finishId || '').toLowerCase();
    var label = String(labelText || '').toLowerCase();
    var score = 0;
    words.forEach(function(word) {
      var clean = word.replace(/^#+/, '');
      if (id === clean) score += 140;
      else if (id.indexOf(clean) >= 0) score += 75;
      if (label.indexOf(clean) >= 0) score += 60;
      if (hay.indexOf(clean) >= 0) score += 25;
      _smartSearchAliasesForWord(clean).forEach(function(alias) {
        if (hay.indexOf(String(alias).toLowerCase()) >= 0) score += 12;
      });
      if (searchKeywords[clean] && finishId && searchKeywords[clean].indexOf(finishId) >= 0) score += 90;
    });
    return score;
  }

  Object.assign(global, {
    FINISH_LIBRARY_SEARCH_ALIASES: FINISH_LIBRARY_SEARCH_ALIASES,
    _smartSearchTokens: _smartSearchTokens,
    _smartSearchAliasesForWord: _smartSearchAliasesForWord,
    _smartSearchWordMatches: _smartSearchWordMatches,
    _smartSearchScore: _smartSearchScore
  });
})(typeof window !== 'undefined' ? window : globalThis);
