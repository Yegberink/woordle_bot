from flask import Flask, render_template, request, jsonify, session
from flask_session import Session
import json
import math
from collections import Counter, defaultdict
import os
from threading import Thread

app = Flask(__name__)

# Configure Flask-Session
app.config['SESSION_TYPE'] = 'filesystem'
app.config['SESSION_FILE_DIR'] = './.flask_session/'
app.config['SESSION_PERMANENT'] = False
Session(app)

# Load data
with open("filtered_dutch_words.txt", "r", encoding="utf-8") as f:
    all_words = [w.strip().lower() for w in f if len(w.strip()) == 5]
with open("word_frequencies.json", "r", encoding="utf-8") as f:
    word_freqs = json.load(f)

# Wordle feedback simulation
def simulate_feedback(guess, target):
    result = ["B"] * 5
    target_letters = list(target)
    for i in range(5):
        if guess[i] == target[i]:
            result[i] = "G"
            target_letters[i] = None
    for i in range(5):
        if result[i] == "B" and guess[i] in target_letters:
            result[i] = "Y"
            target_letters[target_letters.index(guess[i])] = None
    return ''.join(result)

# Entropy calculation
def calculate_entropy_full(possible_words, all_guesses):
    total = len(possible_words)
    entropy_scores = {}
    for guess in all_guesses:
        pattern_counts = defaultdict(int)
        for target in possible_words:
            pattern_counts[simulate_feedback(guess, target)] += 1
        entropy = -sum((count/total) * math.log2(count/total) for count in pattern_counts.values())
        entropy_scores[guess] = entropy
    return entropy_scores

# Precompute initial full-list entropy in background
def _compute_initial_entropy():
    global first_guess_cache, second_guess_cache
    scores = calculate_entropy_full(all_words, all_words)
    top_two = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:2]
    first_guess_cache, second_guess_cache = top_two[0][0], top_two[1][0]

first_guess_cache = None
second_guess_cache = None
Thread(target=_compute_initial_entropy, daemon=True).start()

# Filter words
def filter_words(guess, feedback, words):
    filtered, min_counts = [], {}
    for g, f in zip(guess, feedback):
        if f in ("G","Y"): min_counts[g] = min_counts.get(g,0)+1
    for w in words:
        ok = True; ctr=Counter(w)
        for i,(g,f) in enumerate(zip(guess,feedback)):
            if (f=="G" and w[i]!=g) or (f=="Y" and (g not in w or w[i]==g)) or (f=="B" and w[i]==g): ok=False; break
        if not ok or any(ctr[l]<c for l,c in min_counts.items()): continue
        # extra B handling
        for g,f in zip(guess,feedback):
            if f=="B" and min_counts.get(g,0)==0 and g in ctr: ok=False; break
        if ok: filtered.append(w)
    return filtered

@app.route("/")
def index(): return render_template("index.html")

@app.route("/next", methods=["POST"])
def next_guess():
    guess = request.form.get("guess","").lower()
    feedback = request.form.get("feedback","").upper()
    if "remaining" not in session:
        session["remaining"] = all_words.copy()
        session["history"] = []
    remaining = session["remaining"]
    history = session["history"]
    # apply feedback
    if guess and feedback and len(guess)==5 and len(feedback)==5:
        remaining = filter_words(guess, feedback, remaining)
        history.append({"guess":guess,"feedback":feedback})
        session["history"] = history
    # first guess cache
    if not history and first_guess_cache:
        next_word, second_best = first_guess_cache, second_guess_cache
    else:
        if not remaining:
            next_word, second_best = None, None
        elif len(remaining)<=5:
            scored = sorted(remaining, key=lambda w: word_freqs.get(w,0), reverse=True)
            next_word = scored[0]; second_best = scored[1] if len(scored)>1 else None
        else:
            scores = calculate_entropy_full(remaining, all_words)
            top_two = sorted(scores.items(), key=lambda x:x[1], reverse=True)[:2]
            next_word, second_best = top_two[0][0], top_two[1][0]
    session["remaining"] = remaining
    return jsonify({"guess":next_word,"second_best":second_best,
                    "remaining":remaining[:50],"count":len(remaining),"history":history})

@app.route("/reset", methods=["POST"])
def reset(): session.update({"remaining":all_words.copy(),"history":[]}); return('',204)

if __name__=="__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT",5001)), debug=True)
