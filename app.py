from flask import Flask, render_template, request, jsonify, session
from flask_session import Session
import json
import math
import os
import pickle
from collections import Counter

app = Flask(__name__)


# Configure Flask-Session
app.config['SESSION_TYPE'] = 'filesystem'
app.config['SESSION_FILE_DIR'] = './.flask_session/'
app.config['SESSION_PERMANENT'] = False
Session(app)

# Load word list and frequencies
with open("filtered_dutch_words.txt", "r", encoding="utf-8") as f:
    all_words = [w.strip().lower() for w in f if len(w.strip()) == 5]
with open("word_frequencies.json", "r", encoding="utf-8") as f:
    word_freqs = json.load(f)

# Load precomputed feedback lookup
with open('feedback_lookup.pkl', 'rb') as pkl_file:
    data = pickle.load(pkl_file)
words_list = data['words']  # reference list of all words
feedback_lookup = data['lookup']  # guess -> {pattern: [target_indices]}
# Map word to its index for quick lookup
word_to_index = {w: i for i, w in enumerate(words_list)}

# Filter words based on guess feedback

def filter_words(guess, feedback, words):
    filtered = []
    min_counts = {}

    # Tel minimaal verwachte keren voor G/Y
    for g, f in zip(guess, feedback):
        if f in ("G", "Y"):
            min_counts[g] = min_counts.get(g, 0) + 1

    for w in words:
        ok = True
        ctr = Counter(w)

        for i, (g, f) in enumerate(zip(guess, feedback)):
            if (f == "G" and w[i] != g) or \
               (f == "Y" and (g not in w or w[i] == g)) or \
               (f == "B" and w[i] == g):
                ok = False
                break

        if not ok or any(ctr[l] < c for l, c in min_counts.items()):
            continue

        # Extra black handling: volledig uitsluiten van letters
        for g, f in zip(guess, feedback):
            if f == "B" and min_counts.get(g, 0) == 0 and g in w:
                ok = False
                break

        if ok:
            filtered.append(w)

    return filtered


# Compute entropy using precomputed lookup

def calculate_entropy(remaining, all_guesses):
    total = len(remaining)
    # Precompute remaining indices set
    remaining_indices = {word_to_index[w] for w in remaining}
    entropy_scores = {}

    for guess in all_guesses:
        pattern_map = feedback_lookup.get(guess, {})
        entropy = 0.0
        for count_list in pattern_map.values():
            # count how many targets remain for this pattern
            cnt = len(remaining_indices & set(count_list))
            if cnt == 0:
                continue
            p = cnt / total
            entropy -= p * math.log2(p)
        entropy_scores[guess] = entropy

    return entropy_scores

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/next", methods=["POST"])
def next_guess():
    guess = request.form.get("guess", "").strip().lower()
    feedback = request.form.get("feedback", "").strip().upper()
    if "remaining" not in session:
        session["remaining"] = all_words.copy()
        session["history"] = []

    remaining = session["remaining"]
    history = session["history"]

    # Apply feedback to filter remaining
    if guess and feedback and len(guess) == 5 and len(feedback) == 5:
        remaining = filter_words(guess, feedback, remaining)
        history.append({"guess": guess, "feedback": feedback})
        session["history"] = history

    # Determine next guess
    if not remaining:
        next_word = None
        second_best = None
    elif len(remaining) <= 5:
        scored = sorted(remaining, key=lambda w: word_freqs.get(w, 0), reverse=True)
        next_word = scored[0]
        second_best = scored[1] if len(scored) > 1 else None
    else:
        scores = calculate_entropy(remaining, all_words)

        top_two = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:2]
        next_word, second_best = top_two[0][0], top_two[1][0]

    session["remaining"] = remaining
    
    return jsonify({
        "guess": next_word,
        "second_best": second_best,
        "remaining": remaining[:50],
        "count": len(remaining),
        "history": history
    })

@app.route("/reset", methods=["POST"])
def reset():
    session["remaining"] = all_words.copy()
    session["history"] = []
    return ('', 204)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5002))
    app.run(host="0.0.0.0", port=port, debug=True)