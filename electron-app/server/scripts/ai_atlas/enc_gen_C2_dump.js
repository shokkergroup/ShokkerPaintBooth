// Encyclopedia v2 lane C close-out helper: dumps the shipped help texts (support FAQ/error answers, self-help topics) to JSON on stdout.
// node scripts/ai_atlas/enc_gen_C2_dump.js > out.json     (read-only; fake window, no DOM)
var fs = require('fs'), path = require('path'), vm = require('vm');
var ROOT = path.resolve(__dirname, '..', '..');
function load(file, patch) {
    var src = fs.readFileSync(path.join(ROOT, file), 'utf8');
    if (patch) src = patch(src);
    vm.runInContext(src, ctx, { filename: file });
}
var win = { localStorage: { getItem: function () { return null; }, setItem: function () {} } };
var ctx = vm.createContext({ window: win, console: { log: function () {}, warn: function () {}, error: function () {} }, setTimeout: setTimeout, clearTimeout: clearTimeout, navigator: {}, document: undefined });
win.window = win; ctx.self = win;
try { load('js/spb-support.js'); } catch (e) { process.stderr.write('support load: ' + e.message + '\n'); }
try { load('js/spb-support-answers.js'); } catch (e) { process.stderr.write('answers load: ' + e.message + '\n'); }
try { load('js/spb-self-help.js', function (s) { return s.replace('W.SpbSelfHelp = {', 'W.__TOPICS = TOPICS; W.__L = L; W.SpbSelfHelp = {'); }); } catch (e) { process.stderr.write('selfhelp load: ' + e.message + '\n'); }
var S = win.SpbSupport || {};
var out = {
    faqs: (S.FAQS || []).map(function (f) { return { id: f.id, title: f.title || f.label || null, text: f.answer || null, next: f.next || null }; }),
    errs: (S.ERRS || S.ERRORS || []).map(function (f) { return { id: f.id, title: f.title || null, text: f.answer || null, next: f.next || null }; }),
    supportKeys: Object.keys(S),
    topics: (win.__TOPICS || []).map(function (t) { return { id: t.id, title: t.title, kw: t.kw, steps: t.steps, say: t.say || null, needs: t.needs || null, chat: t.chat || null }; })
};
process.stdout.write(JSON.stringify(out));
