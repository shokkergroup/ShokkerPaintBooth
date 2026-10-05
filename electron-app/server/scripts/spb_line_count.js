'use strict';

const fs = require('fs');

function countTextLines(text) {
  if (!text.length) return 0;
  const lines = text.split(/\r?\n/);
  if (lines[lines.length - 1] === '') lines.pop();
  return lines.length;
}

function countFileLines(filePath) {
  return countTextLines(fs.readFileSync(filePath, 'utf8'));
}

module.exports = {
  countFileLines,
  countTextLines,
};
