'use strict';

const { countTextLines } = require('./spb_line_count');

const cases = [
  ['', 0],
  ['a', 1],
  ['a\n', 1],
  ['a\nb', 2],
  ['a\nb\n', 2],
  ['a\r\nb\r\n', 2],
  ['a\n\nb\n', 3],
];

for (const [text, want] of cases) {
  const got = countTextLines(text);
  if (got !== want) {
    console.error(`line-count guard failed: ${JSON.stringify(text)} got ${got}, want ${want}`);
    process.exit(1);
  }
}

console.log('Line-count guard passed.');
