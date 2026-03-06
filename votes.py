#!/usr/bin/env python3
import json, os, sys, hashlib

VOTES_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "votes.json")

def load_votes():
    if os.path.exists(VOTES_FILE):
        with open(VOTES_FILE) as f:
            return json.load(f)
    return {}

def save_votes(votes):
    with open(VOTES_FILE, 'w') as f:
        json.dump(votes, f)

def get_request_data():
    content_length = int(os.environ.get('CONTENT_LENGTH', 0))
    if content_length:
        body = sys.stdin.read(content_length)
        return json.loads(body)
    return {}

def get_user_id():
    remote = os.environ.get('REMOTE_ADDR', 'unknown')
    ua = os.environ.get('HTTP_USER_AGENT', 'unknown')
    raw = f"{remote}_{ua}"
    return hashlib.md5(raw.encode()).hexdigest()[:12]

def compute_scoreboard(votes):
    combos = {
        "ElevenLabs_V2": {"total_clips": 84, "good": 0, "pass": 0, "bad": 0, "rated": 0},
        "ElevenLabs_V3": {"total_clips": 84, "good": 0, "pass": 0, "bad": 0, "rated": 0},
        "Hume AI_V2": {"total_clips": 28, "good": 0, "pass": 0, "bad": 0, "rated": 0},
        "Hume AI_V3": {"total_clips": 28, "good": 0, "pass": 0, "bad": 0, "rated": 0},
    }
    clip_ratings = {}
    for uid, user_votes in votes.items():
        for rid, data in user_votes.items():
            if rid not in clip_ratings:
                clip_ratings[rid] = {"good": 0, "pass": 0, "bad": 0}
            cat = data.get("cat", "")
            if cat in clip_ratings[rid]:
                clip_ratings[rid][cat] += 1
    for rid, counts in clip_ratings.items():
        parts = rid.split("_")
        if len(parts) >= 3:
            plat = parts[1]
            ver = parts[2]
            key = f"ElevenLabs_{ver.upper()}" if plat == "el" else f"Hume AI_{ver.upper()}"
            if key in combos:
                total = counts["good"] + counts["pass"] + counts["bad"]
                if total > 0:
                    combos[key]["rated"] += 1
                    best = max(counts, key=counts.get)
                    combos[key][best] += 1
    result = {}
    for key, data in combos.items():
        rated = data["rated"]
        if rated > 0:
            result[key] = {
                "total_clips": data["total_clips"], "rated": rated,
                "good": data["good"], "good_pct": round(data["good"]/rated*100,1),
                "pass": data["pass"], "pass_pct": round(data["pass"]/rated*100,1),
                "bad": data["bad"], "bad_pct": round(data["bad"]/rated*100,1),
            }
        else:
            result[key] = {"total_clips": data["total_clips"], "rated": 0,
                "good": 0, "good_pct": 0, "pass": 0, "pass_pct": 0, "bad": 0, "bad_pct": 0}
    return result, len(votes)

method = os.environ.get('REQUEST_METHOD', 'GET')
print("Content-Type: application/json")
print("Access-Control-Allow-Origin: *")
print("Access-Control-Allow-Methods: GET, POST, OPTIONS")
print("Access-Control-Allow-Headers: Content-Type")
print()
if method == 'OPTIONS':
    print('{}')
elif method == 'GET':
    votes = load_votes()
    uid = get_user_id()
    scoreboard, num_voters = compute_scoreboard(votes)
    print(json.dumps({"user_id": uid, "user_votes": votes.get(uid, {}),
        "scoreboard": scoreboard, "num_voters": num_voters,
        "total_ratings": sum(len(v) for v in votes.values())}))
elif method == 'POST':
    data = get_request_data()
    action = data.get("action", "")
    uid = get_user_id()
    votes = load_votes()
    if action == "rate":
        rid = data.get("rid", "")
        cat = data.get("cat", "")
        vote_data = data.get("data", {})
        if uid not in votes: votes[uid] = {}
        if cat:
            votes[uid][rid] = {"cat": cat, **vote_data}
        elif rid in votes[uid]:
            del votes[uid][rid]
        save_votes(votes)
        scoreboard, num_voters = compute_scoreboard(votes)
        print(json.dumps({"ok": True, "user_votes": votes[uid],
            "scoreboard": scoreboard, "num_voters": num_voters,
            "total_ratings": sum(len(v) for v in votes.values())}))
    elif action == "clear":
        if uid in votes: del votes[uid]
        save_votes(votes)
        scoreboard, num_voters = compute_scoreboard(votes)
        print(json.dumps({"ok": True, "user_votes": {},
            "scoreboard": scoreboard, "num_voters": num_voters,
            "total_ratings": sum(len(v) for v in votes.values())}))
    else:
        print(json.dumps({"error": "Unknown action"}))
