from flask import Flask, render_template, request, jsonify, session
from flask_session import Session
import csv
import math
from collections import Counter, defaultdict
import os
import json

app = Flask(__name__)

# Configure Flask-Session to store data server-side (on the filesystem)
app.config['SESSION_TYPE'] = 'filesystem'
app.config['SESSION_FILE_DIR'] = './.flask_session/'
app.config['SESSION_PERMANENT'] = False
Session(app)

# Load word list
with open("filtered_dutch_words.txt", "r", encoding="utf-8") as f:
    all_words = [line.strip().lower() for line in f if len(line.strip()) == 5]

# Load word frequencies
with open("word_frequencies.json", encoding="utf-8") as f:
    word_freqs = json.load(f)

def simulate_feedback(guess, target):
    result = ["B"] * 5
    target_letters = list(target)

    # First pass: correct letters in correct position
    for i in range(5):
        if guess[i] == target[i]:
            result[i] = "G"
            target_letters[i] = None  # mark used

    # Second pass: correct letters in wrong position
    for i in range(5):
        if result[i] == "B" and guess[i] in target_letters:
            result[i] = "Y"
            target_letters[target_letters.index(guess[i])] = None  # mark used

    return "".join(result)

def calculate_entropy_full(possible_words, all_guesses):
    entropy_scores = {}

    for guess in all_guesses:
        pattern_counts = defaultdict(int)

        for target in possible_words:
            pattern = simulate_feedback(guess, target)
            pattern_counts[pattern] += 1

        total = len(possible_words)
        entropy = 0
        for count in pattern_counts.values():
            p = count / total
            entropy -= p * math.log2(p)
        entropy_scores[guess] = entropy

    return entropy_scores

def find_occurence(possible_words):
    return {word: word_freqs.get(word.lower(), 0) for word in possible_words}

def filter_words(guess, feedback, words):
    filtered = []
    min_counts = {}

    for g, f in zip(guess, feedback):
        if f in ("G", "Y"):
            min_counts[g] = min_counts.get(g, 0) + 1

    for word in words:
        match = True

        for i in range(5):
            g = guess[i]
            f = feedback[i]

            if f == "G":
                if word[i] != g:
                    match = False
                    break
            elif f == "Y":
                if g not in word or word[i] == g:
                    match = False
                    break
            elif f == "B":
                if word[i] == g:
                    match = False
                    break

        if not match:
            continue

        word_counts = Counter(word)
        for letter, count in min_counts.items():
            if word_counts.get(letter, 0) < count:
                match = False
                break

        for i in range(5):
            g = guess[i]
            f = feedback[i]
            if f == "B" and min_counts.get(g, 0) == 0 and g in word:
                match = False
                break

        if match:
            filtered.append(word)

    return filtered

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/next", methods=["POST"])
def next_guess():
    guess = request.form.get("guess", "").lower()
    feedback = request.form.get("feedback", "").upper()

    if "remaining" not in session:
        session["remaining"] = all_words.copy()
        session["history"] = []

    remaining = session["remaining"]
    history = session["history"]

    if guess and feedback and len(guess) == 5 and len(feedback) == 5:
        remaining = filter_words(guess, feedback, remaining)
        history.append({"guess": guess, "feedback": feedback})
        session["history"] = history

    if len(remaining) == 0:
        next_word = None
        second_best = None
    elif len(remaining) == 1:
        next_word = remaining[0]
        second_best = None
    elif 1 < len(remaining) <= 5:
        scores = find_occurence(remaining)
        top_two = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:2]
        next_word = top_two[0][0]
        second_best = top_two[1][0] if len(top_two) > 1 else None
    else:
        # Main improvement: consider *all* words for entropy calculation
        scores = calculate_entropy_full(remaining, all_words)
        top_two = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:2]
        next_word = top_two[0][0]
        second_best = top_two[1][0] if len(top_two) > 1 else None

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
    return "", 204

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5001))
    app.run(host="0.0.0.0", port=port, debug=True)
