"""Train the small OFFLINE intent model for the finish advisor (2026-10-03 night).  Data: the independent Codex L3 corpus (1,500 labelled messages, 13 intents) + the 400 truth asks (recommend).
   python scripts/ai_atlas/train_intent.py --eval                 # train on even rows, test on odd rows (and the reverse): accuracy, finish-vs-other precision / recall, confusion
   python scripts/ai_atlas/train_intent.py --export               # train on everything, write js/spb-intent-data.js  (loaded by js/spb-intent.js)
The model is a multinomial logistic regression over word 1-2 grams; the JS side only needs the pruned weight table (no runtime cost, no network)."""
import os, sys, json, re, collections, argparse
import numpy as np
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.linear_model import LogisticRegression
sys.stdout.reconfigure(encoding='utf-8')
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
CORPUS = os.path.join(ROOT, '_codex_work', 'finish_intel', 'l3_intent_corpus', 'intent_corpus.jsonl')
TRUTH = os.path.join(ROOT, '_codex_work', 'finish_intel', 'l2_truth_asks', 'truth_asks.json')
FINISH = ['recommend', 'find', 'compare', 'about', 'kit', 'review', 'taste', 'judge', 'inspect', 'catalogue']


def norm(t):
    t = str(t).lower().replace('’', "'").replace('`', "'")
    t = re.sub(r'\d+', '0', t)
    return ' '.join(re.findall(r"[a-z']+|0", t))


def load():
    rows = [json.loads(l) for l in open(CORPUS, encoding='utf-8') if l.strip()]
    X = [norm(r['text']) for r in rows]; y = [r['intent'] for r in rows]
    ex = [norm(t['ask']) for t in json.load(open(TRUTH, encoding='utf-8'))]
    # the maintainers' own hand-written negatives (design orders / app questions), three times over: they are the phrases real buyers type
    negp = os.path.join(ROOT, '_easy_claude_work', 'neg_prompts.txt')
    if os.path.exists(negp):
        for l in open(negp, encoding='utf-8'):
            l = l.strip()
            if not l:
                continue
            lab = 'support' if re.match(r"(how |why |where |what('s| is) (a |the )?(zone|base colou?r|spec|my customer)|what does the|what size|can i use|is my paint|what can you do|undo|start over)", l.lower()) else 'design'
            for _ in range(3):
                X.append(norm(l)); y.append(lab)
    # the advisor's own reviewed rule behaviour on the maintainers' positive prompt files (what finish do I put on the roof = recommend, not a state question)
    fp = os.path.join(ROOT, '_easy_claude_work', 'fp_rules.txt')
    MAP = {'recommend': 'recommend', 'find': 'find', 'compare': 'compare', 'about': 'about', 'inspect': 'inspect', 'judge': 'judge', 'taste': 'taste', 'catalogue': 'catalogue', 'review': 'review', 'kit': 'kit', 'simlook': 'about', 'pairs': 'recommend'}
    if os.path.exists(fp):
        for l in open(fp, encoding='utf-8'):
            parts = l.rstrip('\n').split(None, 2)
            if len(parts) == 3 and parts[0] in MAP:
                for _ in range(2):
                    X.append(norm(parts[2])); y.append(MAP[parts[0]])
    return X, y, ex


def fit(X, y, extra=()):
    Xa = list(X) + list(extra); ya = list(y) + ['recommend'] * len(extra)
    vec = CountVectorizer(ngram_range=(1, 2), min_df=2, binary=True, token_pattern=r"[a-z']+|0")
    M = vec.fit_transform(Xa)
    clf = LogisticRegression(C=8.0, max_iter=3000)
    clf.fit(M, ya)
    return vec, clf


def evaluate():
    X, y, ex = load(); n = 1500
    tot = []; allp = []
    for fold in (0, 1):
        tr = [i for i in range(n) if i % 2 != fold] + list(range(n, len(X))); te = [i for i in range(n) if i % 2 == fold]
        vec, clf = fit([X[i] for i in tr], [y[i] for i in tr], [e for j, e in enumerate(ex) if j % 2 != fold])
        pred = clf.predict(vec.transform([X[i] for i in te])); prob = clf.predict_proba(vec.transform([X[i] for i in te])).max(axis=1)
        for i, p, q in zip(te, pred, prob):
            allp.append((i, y[i], p, q))
    acc = sum(1 for _, a, b, _ in allp if a == b) / len(allp)
    print('13-way accuracy (2-fold, even/odd): %.1f%% over %d' % (100 * acc, len(allp)))
    fin_true = [a in FINISH for _, a, _, _ in allp]; fin_pred = [b in FINISH for _, _, b, _ in allp]
    tp = sum(1 for a, b in zip(fin_true, fin_pred) if a and b); fp = sum(1 for a, b in zip(fin_true, fin_pred) if (not a) and b); fn = sum(1 for a, b in zip(fin_true, fin_pred) if a and (not b))
    print('finish vs other: precision %.1f%%  recall %.1f%%  (fp %d, fn %d)' % (100 * tp / max(1, tp + fp), 100 * tp / max(1, tp + fn), fp, fn))
    for thr in (0.5, 0.6, 0.7, 0.8):
        sel = [(a, b) for _, a, b, q in allp if q >= thr]
        print('  confidence >= %.1f: covers %.0f%% of messages, label accuracy %.1f%%' % (thr, 100 * len(sel) / len(allp), 100 * sum(1 for a, b in sel if a == b) / max(1, len(sel))))
    per = collections.defaultdict(lambda: [0, 0])
    for _, a, b, _ in allp:
        per[a][0] += 1; per[a][1] += (a == b)
    print('per label recall: ' + '  '.join('%s %.0f%%' % (k, 100 * v[1] / v[0]) for k, v in sorted(per.items())))
    conf = collections.Counter((a, b) for _, a, b, _ in allp if a != b)
    print('top confusions: ' + '; '.join('%s->%s %d' % (a, b, c) for (a, b), c in conf.most_common(10)))


def export(K=3500, fold=None, outp=None):
    X, y, ex = load()
    if fold is None:
        vec, clf = fit(X, y, ex)
    else:       # a model that never saw the rows i % 2 == fold: for an honest end-to-end evaluation of the integrated classifier
        keep = [i for i in range(len(X)) if i >= 1500 or i % 2 != fold]
        vec, clf = fit([X[i] for i in keep], [y[i] for i in keep], [e for j, e in enumerate(ex) if j % 2 != fold])
    vocab = vec.get_feature_names_out(); W = clf.coef_; classes = list(clf.classes_)
    score = np.abs(W).max(axis=0); keep = np.argsort(-score)[:K]; keep.sort()
    feats = [str(vocab[i]) for i in keep]; weights = [[int(round(W[c, i] * 100)) for i in keep] for c in range(len(classes))]
    icpt = [int(round(v * 100)) for v in clf.intercept_]
    out = {'classes': classes, 'features': feats, 'weights': weights, 'intercept': icpt, 'n_train': len(X) + len(ex)}
    js = '/* generated by scripts/ai_atlas/train_intent.py (do not edit): the offline intent model of the finish advisor */\nwindow.SPB_INTENT_DATA = ' + json.dumps(out, separators=(',', ':')) + ';\n'
    p = outp or os.path.join(ROOT, 'js', 'spb-intent-data.js'); open(p, 'w', encoding='utf-8', newline='').write(js)
    print('wrote', p, len(js), 'bytes;', len(feats), 'features x', len(classes), 'classes')


ap = argparse.ArgumentParser(); ap.add_argument('--eval', action='store_true'); ap.add_argument('--export', action='store_true'); ap.add_argument('--k', type=int, default=3500); ap.add_argument('--fold', type=int, default=None); ap.add_argument('--out', default=None); a = ap.parse_args()
if a.eval or not a.export:
    evaluate()
if a.export:
    export(a.k, a.fold, a.out)
