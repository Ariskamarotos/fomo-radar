"""FOMO snapshot collector. Never relabel stale upstream data as live."""
import json, os, urllib.request, urllib.error, datetime, time
from pathlib import Path

URL = 'https://api.fomoapi.io/v2/leaderboard/tokens/trending?limit=25'
KEY = os.environ.get('FOMO_API_KEY')
if not KEY:
    raise SystemExit('Missing FOMO_API_KEY GitHub secret')
Path('data').mkdir(exist_ok=True)
now = datetime.datetime.now(datetime.timezone.utc)
stamp = now.isoformat().replace('+00:00', 'Z')

def fetch(url):
    req = urllib.request.Request(url, headers={
        'Authorization': f'Bearer {KEY}', 'Accept': 'application/json',
        'User-Agent': 'fomo-radar-github-actions/1.0'})
    with urllib.request.urlopen(req, timeout=40) as response:
        return json.load(response)

def is_fresh(payload):
    if not isinstance(payload, dict) or not isinstance(payload.get('tokens'), list) or not payload['tokens']:
        return False, 'empty_or_invalid_tokens'
    if payload.get('source') != 'live-fomo' or payload.get('stale') is True:
        return False, 'upstream_source_not_live_or_stale'
    captured = payload.get('capturedAt')
    if not captured:
        return False, 'missing_capturedAt'
    try:
        dt = datetime.datetime.fromisoformat(captured.replace('Z', '+00:00'))
        age = (datetime.datetime.now(datetime.timezone.utc) - dt).total_seconds()
    except (TypeError, ValueError):
        return False, 'invalid_capturedAt'
    if age < -120 or age > 900:
        return False, f'upstream_capture_age_seconds={round(age)}'
    return True, 'fresh'

payload = None
reason = 'not_attempted'
for attempt in range(3):
    try:
        candidate = fetch(URL)
        valid, reason = is_fresh(candidate)
        if valid:
            payload = candidate
            break
        print(f'Attempt {attempt+1}: rejected FOMO response ({reason}); source={candidate.get("source") if isinstance(candidate, dict) else "invalid"}, stale={candidate.get("stale") if isinstance(candidate, dict) else "unknown"}')
    except urllib.error.HTTPError as exc:
        reason = f'http_{exc.code}'
        print(f'Attempt {attempt+1}: FOMO HTTP {exc.code}')
        if exc.code in (401, 403):
            break
    except (urllib.error.URLError, TimeoutError, ValueError, OSError) as exc:
        reason = type(exc).__name__
        print(f'Attempt {attempt+1}: {reason}')
    if attempt < 2:
        time.sleep(5 * (attempt + 1))

status = {'checkedAt': datetime.datetime.now(datetime.timezone.utc).isoformat().replace('+00:00','Z'),
          'fresh': payload is not None, 'reason': reason,
          'message': 'Upstream freshness is mandatory. No stale data was relabeled as current.'}
Path('data/collector_status.json').write_text(json.dumps(status, indent=2)+'\n', encoding='utf-8')
if payload is None:
    print(f'::warning::FOMO provider degraded ({reason}); keeping last good snapshots unchanged')
    raise SystemExit(0)

allowed = []
for token in payload['tokens'][:25]:
    info = token.get('token') or {}
    allowed.append({'rank': token.get('rank'), 'symbol': info.get('symbol'),
                    'name': info.get('name'), 'address': info.get('address'),
                    'network': token.get('network'), 'marketCapUsd': token.get('marketCapUsd'),
                    'holders': token.get('holders'), 'change24h': token.get('change24h'),
                    'priceUsd': token.get('priceUsd')})
output = {'polledAt': stamp, 'capturedAt': payload.get('capturedAt'),
          'source': payload.get('source'), 'stale': False, 'count': len(allowed),
          'tokens': allowed,
          'warning': 'Unofficial third-party API. Not an independently verified security audit.'}
Path('data/trending.json').write_text(json.dumps(output, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
print(f'Wrote {len(allowed)} fresh tokens at {stamp}')

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
