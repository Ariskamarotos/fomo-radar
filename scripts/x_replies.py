"""Read-only X reply detector. Disabled until explicitly enabled in a workflow.
Stores minimal metadata, no credentials, no private content. API billing applies.
"""
import datetime
import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

BASE = "https://api.x.com/2"
USERS = ("blknoiz06", "MINHxDYNASTY")
OUT = Path("data/x_signals.json")
STATE = Path("data/x_state.json")

def request(path, bearer):
    req = urllib.request.Request(BASE + path, headers={
        "Authorization": "Bearer " + bearer, "Accept": "application/json",
        "User-Agent": "fomo-radar-reply-detector/0.1"})
    with urllib.request.urlopen(req, timeout=20) as response:
        return json.load(response)

TOKEN_TERMS = re.compile(r"(?i)(\b(?:token|coin|memecoin|pump|contract|buy|ape|launch|ticker|dex|liquidity|solana)\b|\$[A-Za-z][A-Za-z0-9]{1,12}\b|[1-9A-HJ-NP-Za-km-z]{32,44})")

def relevant(text):
    return bool(TOKEN_TERMS.search(text or ""))

def parse_replies(username, posts):
    signals = []
    for post in posts:
        references = post.get("referenced_tweets") or []
        if not any(r.get("type") == "replied_to" for r in references):
            continue
        signals.append({
            "account": username, "postId": post["id"],
            "url": f"https://x.com/{username}/status/{post['id']}",
            "createdAt": post.get("created_at"),
            "replyToId": next((r.get("id") for r in references if r.get("type") == "replied_to"), None),
            "text": post.get("text", "")[:1000],
            "tokenRelated": relevant(post.get("text", "")), "verifiedToken": False,
            "marketReaction": "not_assessed"})
    return signals

def main():
    bearer = os.environ.get("X_BEARER_TOKEN")
    if not bearer:
        raise SystemExit("Missing X_BEARER_TOKEN")
    previous = json.loads(STATE.read_text()) if STATE.exists() else {}
    new_state = dict(previous)
    all_signals = []
    failures = []
    account_status = {}
    for username in USERS:
        try:
            user = request("/users/by/username/" + urllib.parse.quote(username) + "?user.fields=id", bearer).get("data") or {}
            uid = user.get("id")
            if not uid:
                failures.append({"account": username, "reason": "user_not_found"})
                account_status[username] = {"status": "user_not_found", "postsReturned": 0}
                continue
            params = {"max_results": "10", "tweet.fields": "created_at,referenced_tweets"}
            if previous.get(username):
                params["since_id"] = str(previous[username])
            payload = request("/users/" + urllib.parse.quote(uid) + "/tweets?" + urllib.parse.urlencode(params), bearer)
            posts = payload.get("data") or []
            replies = parse_replies(username, posts)
            all_signals.extend(replies)
            account_status[username] = {"status": "ok" if posts else "empty_feed",
                                        "postsReturned": len(posts), "repliesFound": len(replies),
                                        "latestPostId": str(max(int(p["id"]) for p in posts)) if posts else None,
                                        "cursorBefore": previous.get(username),
                                        "note": "No posts returned; cannot confirm coverage" if not posts else None}
            if posts:
                new_state[username] = str(max(int(p["id"]) for p in posts))
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, ValueError, KeyError) as exc:
            account_status[username] = {"status": "error", "postsReturned": 0}
            failures.append({"account": username, "reason": type(exc).__name__,
                             "httpStatus": getattr(exc, "code", None)})
    # Preserve previous cursors on failure. Never print credentials.
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({"checkedAt": now, "accounts": list(USERS),
        "signals": [s for s in all_signals if s["tokenRelated"]], "totalRepliesScanned": len(all_signals), "accountStatus": account_status, "errors": failures,
        "note": "Replies are unverified social signals, not evidence of purchases or endorsement."},
        indent=2, ensure_ascii=False) + "\n")
    STATE.write_text(json.dumps(new_state, indent=2) + "\n")
    print(f"X reply detector: {len(all_signals)} replies, {len(failures)} account errors")

if __name__ == "__main__":
    main()
