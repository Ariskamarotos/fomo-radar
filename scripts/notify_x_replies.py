"""Send deduplicated ntfy alerts for newly detected X token-related replies.
Requires NTFY_TOPIC secret. Not a verified trading recommendation.
"""
import json
import os
import urllib.parse
import urllib.request
from pathlib import Path

SIGNALS = Path("data/x_signals.json")
SENT = Path("data/x_notified.json")

def pending(signals, notified):
    known = set(notified)
    return [s for s in signals if s.get("tokenRelated") is True and
            str(s.get("postId", "")) not in known and s.get("url", "").startswith("https://x.com/")]

def main():
    topic = os.environ.get("NTFY_TOPIC", "").strip()
    if not topic:
        print("NTFY_TOPIC not configured; skipping push notifications")
        return
    if not all(c.isalnum() or c in "-_" for c in topic) or len(topic) < 24:
        raise SystemExit("NTFY_TOPIC must be an unguessable 24+ character topic name")
    data = json.loads(SIGNALS.read_text()) if SIGNALS.exists() else {}
    notified = json.loads(SENT.read_text()) if SENT.exists() else []
    if data.get("errors"):
        print("Some X API errors occurred; processing only returned signals")
    candidates = pending(data.get("signals", []), notified)
    for signal in candidates:
        account = signal["account"]
        message = f"@{account}: {signal.get('text', '')[:350]}\\n{signal['url']}\\nUnverified X reply; not a token endorsement."
        request = urllib.request.Request(
            "https://ntfy.sh/" + urllib.parse.quote(topic, safe=""),
            data=message.encode("utf-8"),
            headers={"Title": f"X token-related reply: @{account}",
                     "Priority": "4", "Tags": "eyes",
                     "Click": signal["url"], "Content-Type": "text/plain; charset=utf-8"},
            method="POST")
        with urllib.request.urlopen(request, timeout=20) as response:
            if response.status >= 300:
                raise RuntimeError("ntfy push failed")
        notified.append(str(signal["postId"]))
        SENT.parent.mkdir(parents=True, exist_ok=True)
        SENT.write_text(json.dumps(notified[-1000:], indent=2) + "\\n")
    print(f"Sent {len(candidates)} ntfy alert(s)")

if __name__ == "__main__":
    main()
