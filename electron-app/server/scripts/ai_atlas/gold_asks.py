"""Generate the GOLD ASKS: realistic painter-voice requests (what people actually type into the copilot) used to MEASURE finish search / advice.
python scripts/ai_atlas/gold_asks.py            ->  _easy_claude_work/gold/asks.json   [{ask, cat}]
Categories are written to cover the whole space (class of car, mood, materials, sponsor vibes, parts, colour schemes, sim constraints, negatives, seasons, abstract).
The model only WRITES the asks (cheap); relevance is judged later by gold_eval.py from the PICTURES of the results."""
import os, sys, json, re, time, urllib.request, random
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
OUT = os.path.join(ROOT, '_easy_claude_work', 'gold')
BASE = os.environ.get('SPB_CARDS_SERVER', 'http://127.0.0.1:59879')
MODEL = os.environ.get('SPB_CARDS_MODEL', 'deepseek/deepseek-v4.1-flash')
CATS = {
    'class_era': 'the KIND of race car and era: dirt late model, NASCAR Cup, GT3, IndyCar, sprint car, drag car, pickup truck, rally, vintage stock car, 70s muscle, 90s touring car',
    'mood_vibe': 'a mood or personality: aggressive, elegant, playful, menacing, retro, clean, techy, luxury, rugged, dreamy, cold, fiery',
    'real_world': 'a real-world thing the finish should look like: brushed aluminum, wet asphalt, bourbon barrel, guitar sunburst, cut gemstone, leather seat, beer can, watch dial, ocean, desert sand, lava, snake skin',
    'sponsor_vibe': 'the feel of a sponsor or brand: energy drink, whiskey, bank, tool company, outdoors, military, sneaker brand, local pizza shop, craft beer, tech startup, tribute to a driver',
    'part_context': 'a specific part with the colours already chosen: stripes on a navy car, hood on an orange and black scheme, roof on a white car, spoiler, bumpers, lower band, door numbers; they ask what finish suits it',
    'scheme_pairing': 'they describe their colour scheme and ask what finish or finish combination fits: for example navy and orange, red white and blue, black and gold, lime and purple, all white, matte olive',
    'sim_constraints': 'practical iRacing concerns: readability at speed, TV camera, glare in sunlight, night races, looks good from far away, render speed, not going dark in the sim',
    'negatives': 'requests with something to AVOID: not too shiny, nothing sparkly, no rainbow, not cheap-looking, not too busy, no chrome, keep the numbers clean',
    'seasonal_tribute': 'holidays, seasons, tributes and themes: Halloween, Christmas, 4th of July, memorial car, charity pink car, Mexican heritage, Japanese street racing, retro Gulf livery',
    'abstract_wild': 'abstract or wild asks: something nobody else has, looks alive, looks like a galaxy, glitchy, looks like it is made of glass, looks expensive but weird, looks like liquid metal'
}
SYS = 'You write realistic test requests for a car-paint design assistant. You are one of many iRacing painters typing quickly into a chat box: casual, short, sometimes lower case or a typo, never polite boilerplate.'


def post(body):
    req = urllib.request.Request(BASE + '/api/ai/chat', data=json.dumps(body).encode('utf-8'), headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=150) as r:
        return json.loads(r.read().decode('utf-8'))


def main():
    os.makedirs(OUT, exist_ok=True)
    asks, cost = [], 0.0
    for cat, desc in CATS.items():
        for rnd in range(2):
            user = ('Write 18 DIFFERENT requests a painter might type about finishes (paint materials / effects). Topic: %s. Vary length (3 to 25 words), vary wording, include a few typos, '
                    'include some that give extra context (their colours, the car, the part). Some should be questions, some statements. Reply with ONLY a JSON array of strings. Batch %d: make these clearly different from a typical first batch.') % (desc, rnd + 1)
            for attempt in range(3):
                try:
                    r = post({'model': MODEL, 'messages': [{'role': 'system', 'content': SYS}, {'role': 'user', 'content': user}], 'max_tokens': 1800, 'temperature': 0.95, 'reasoning': {'enabled': False}})
                    if not r.get('ok'):
                        time.sleep(3); continue
                    cost += float((r.get('usage') or {}).get('cost') or 0)
                    m = re.search(r'\[[\s\S]*\]', (r.get('message') or {}).get('content') or '')
                    arr = json.loads(m.group(0)) if m else []
                    for a in arr:
                        a = re.sub(r'\s+', ' ', str(a)).strip()
                        if 8 <= len(a) <= 220 and not any(x['ask'].lower() == a.lower() for x in asks):
                            asks.append({'ask': a, 'cat': cat})
                    break
                except Exception as e:
                    print('retry', cat, e, flush=True); time.sleep(3)
        print(cat, len(asks), '$%.4f' % cost, flush=True)
    random.Random(11).shuffle(asks)
    json.dump(asks, open(os.path.join(OUT, 'asks.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('asks', len(asks), 'cost $%.4f' % cost)


if __name__ == '__main__':
    main()
