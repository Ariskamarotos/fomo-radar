import json, os, urllib.request, urllib.error, datetime
from pathlib import Path

URL = 'https://api.fomoapi.io/v2/leaderboard/tokens/trending?limit=25'
KEY = os.environ.get('FOMO_API_KEY')
if not KEY:
    raise SystemExit('Missing FOMO_API_KEY GitHub secret')
req = urllib.request.Request(URL, headers={'Authorization': f'Bearer {KEY}', 'Accept': 'application/json','User-Agent':'fomo-radar-github-actions/1.0'})
try:
    with urllib.request.urlopen(req, timeout=40) as response:
        payload = json.load(response)
except urllib.error.HTTPError as err:
    raise SystemExit(f'FOMO API returned HTTP {err.code}; check key, credits and service status')
if not isinstance(payload,dict) or not isinstance(payload.get('tokens'),list) or not payload['tokens']:
    raise SystemExit('FOMO API returned missing/empty tokens; not replacing last good snapshot')
if payload.get('source') != 'live-fomo' or payload.get('stale') is True:
    raise SystemExit('FOMO board does not report fresh live source; not replacing last good snapshot')
now=datetime.datetime.now(datetime.timezone.utc).isoformat().replace('+00:00','Z')
allowed=[]
for token in payload['tokens'][:25]:
    info=token.get('token') or {}
    allowed.append({'rank':token.get('rank'), 'symbol':info.get('symbol'), 'name':info.get('name'), 'address':info.get('address'), 'network':token.get('network'), 'marketCapUsd':token.get('marketCapUsd'), 'holders':token.get('holders'), 'change24h':token.get('change24h'), 'priceUsd':token.get('priceUsd')})
output={'polledAt':now, 'capturedAt':payload.get('capturedAt'),'source':payload.get('source'),'stale':payload.get('stale'),'count':len(allowed),'tokens':allowed,'warning':'Unofficial third-party API. Snapshot is not an independently verified signal, liquidity estimate or security audit.'}
Path('data').mkdir(exist_ok=True)
Path('data/trending.json').write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(f'Wrote {len(allowed)} token records at {now}; no API key stored')


# Independent graduated board for early narrative discovery; preserve trending unchanged.
graduated_url = 'https://api.fomoapi.io/v2/leaderboard/tokens/graduated?limit=50'
graduated_req = urllib.request.Request(graduated_url, headers={'Authorization': f'Bearer {KEY}', 'Accept': 'application/json', 'User-Agent': 'fomo-radar-github-actions/1.0'})
try:
    with urllib.request.urlopen(graduated_req, timeout=40) as response:
        graduated = json.load(response)
    if isinstance(graduated, dict) and graduated.get('source') == 'live-fomo' and graduated.get('stale') is not True and isinstance(graduated.get('tokens'), list):
        entries = []
        for item in graduated['tokens'][:50]:
            info = item.get('token') or {}
            entries.append({'rank': item.get('rank'), 'symbol': info.get('symbol'), 'name': info.get('name'), 'address': info.get('address'), 'network': item.get('network'), 'marketCapUsd': item.get('marketCapUsd'), 'holders': item.get('holders'), 'change24h': item.get('change24h'), 'priceUsd': item.get('priceUsd')})
        Path('data/graduated.json').write_text(json.dumps({'polledAt': datetime.datetime.now(datetime.timezone.utc).isoformat().replace('+00:00','Z'), 'capturedAt': graduated.get('capturedAt'), 'source': graduated.get('source'), 'stale': graduated.get('stale'), 'count': len(entries), 'tokens': entries, 'warning': 'Narrative discovery candidates only; no security verification or buy recommendation.'}, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
        print(f'Wrote {len(entries)} graduated candidates')
    else:
        print('Graduated board unavailable or stale; keeping previous snapshot')
except (urllib.error.URLError, TimeoutError, ValueError, OSError) as exc:
    print(f'Graduated board fetch failed ({type(exc).__name__}); keeping previous snapshot')
