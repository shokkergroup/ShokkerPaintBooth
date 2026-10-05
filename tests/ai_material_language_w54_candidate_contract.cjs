// W54 fresh oracle frozen before inspecting the route/controller implementation.
// These cases target natural multi-channel, negation, and preservation language.
const cases = [
  { id: 'clearcoat-while-keeping-roughness', text: 'Make the roof less clearcoated while keeping roughness the same.', target: 'roof', expected: 'safe-preserve-or-clarify' },
  { id: 'rougher-leave-metalness', text: 'Leave metalness alone but make the roof rougher.', target: 'roof', expected: 'roughness-only-or-clarify' },
  { id: 'double-negation', text: "Don't not lower clearcoat on the roof; keep roughness unchanged.", target: 'roof', expected: 'clarify-zero-edit' },
  { id: 'conflicting-clearcoat', text: 'Lower clearcoat on the roof by 10 points, but raise clearcoat on the roof by 5 points.', target: 'roof', expected: 'clarify-zero-edit' },
  { id: 'two-explicit-channels', text: 'Lower clearcoat on the roof by 10 points and raise roughness on the roof by 15 points.', target: 'roof', expected: 'both-channels-or-clarify' },
  { id: 'preserve-roughness', text: 'Lower clearcoat on the roof by 10 points while keeping roughness unchanged.', target: 'roof', expected: 'clearcoat-only-or-clarify' },
  { id: 'preserve-metalness', text: 'Please leave roof metalness alone and make its clearcoat less shiny.', target: 'roof', expected: 'clearcoat-only-or-clarify' },
  { id: 'relative-roughness', text: 'Please raise roughness on the hood by 12 points.', target: 'hood', expected: 'roughness-plus-12' },
  { id: 'relative-clearcoat', text: 'Reduce clearcoat on the roof by 10 points.', target: 'roof', expected: 'clearcoat-minus-10' },
  { id: 'opposing-channel-commands', text: 'Raise roof roughness by 10 points and lower roughness by 4 points.', target: 'roof', expected: 'clarify-zero-edit' },
  { id: 'question-delegates', text: 'How should I adjust clearcoat on the roof?', target: 'roof', expected: 'delegate-no-queue' },
  { id: 'unmentioned-channel-lock', text: 'Lower clearcoat on the roof by 8 points.', target: 'roof', expected: 'clearcoat-only' },
  { id: 'negated-action', text: 'Do not lower clearcoat on the roof.', target: 'roof', expected: 'clarify-zero-edit' },
  { id: 'separate-targets-mixed', text: 'Lower roof clearcoat and raise hood roughness by 10 points.', target: null, expected: 'clarify-zero-edit' },
];
if (cases.length < 12) throw new Error('W54 oracle must contain at least 12 fresh cases');
module.exports = { cases };
