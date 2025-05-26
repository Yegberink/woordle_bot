from flask import Flask, render_template, request, jsonify, session
from flask_session import Session
import csv
import math
from collections import Counter
import os

app = Flask(__name__)

# Configure Flask-Session to store data server-side (on the filesystem)
app.config['SESSION_TYPE'] = 'filesystem'
app.config['SESSION_FILE_DIR'] = './.flask_session/'
app.config['SESSION_PERMANENT'] = False
Session(app)

# Load word list
with open("filtered_dutch_words.txt", "r", encoding="utf-8") as f:
    all_words = [line.strip().lower() for line in f if len(line.strip()) == 5]

def calculate_entropy(possible_words):
    letter_positions = [{} for _ in range(5)]
    for word in possible_words:
        for i, letter in enumerate(word):
            letter_positions[i][letter] = letter_positions[i].get(letter, 0) + 1

    entropy_scores = {}
    for word in all_words:
        score = 0
        seen = set()
        for i, letter in enumerate(word):
            if letter not in seen:
                freq = letter_positions[i].get(letter, 0)
                prob = freq / len(possible_words)
                if prob > 0:
                    score += -prob * math.log2(prob)
                seen.add(letter)
        entropy_scores[word] = score
    return entropy_scores

def filter_words(guess, feedback, words):
    filtered = []
    
    # Count minimal number of occurrences required for each letter (green + yellow)
    min_counts = {}
    for g, f in zip(guess, feedback):
        if f in ("G", "Y"):
            min_counts[g] = min_counts.get(g, 0) + 1

    for word in words:
        match = True

        # Check green and black/yellow positional constraints
        for i in range(5):
            g = guess[i]
            f = feedback[i]

            if f == "G":
                # Must match the letter exactly here
                if word[i] != g:
                    match = False
                    break
            elif f == "Y":
                # Letter must be elsewhere, not here
                if g not in word or word[i] == g:
                    match = False
                    break
            elif f == "B":
                # Black: letter count in word should be <= min_count (i.e. exclude extra occurrences)
                # And the letter should NOT be at this position
                # But if the letter is required elsewhere (green/yellow), it can exist up to min_count
                # So we check the total count of g in word
                # If g is not in min_counts, min_counts.get(g,0) will be 0
                if word[i] == g:
                    match = False
                    break

        if not match:
            continue

        # Check letter counts vs min_counts
        word_counts = Counter(word)
        for letter, count in min_counts.items():
            if word_counts.get(letter, 0) < count:
                match = False
                break

        # Also, letters marked black in guess but with min_count == 0 should NOT appear in the word
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
    guess = request.form.get("guess")
    feedback = request.form.get("feedback")

    # Initialize session state if not present
    if "remaining" not in session:
        session["remaining"] = all_words.copy()
        session["history"] = []

    remaining = session["remaining"]
    history = session["history"]

    if guess and feedback:
        remaining = filter_words(guess, feedback, remaining)
        history.append({"guess": guess, "feedback": feedback})
        session["history"] = history

    if len(remaining) == 1:
        next_word = remaining[0]
        second_best = None
    else:
        scores = calculate_entropy(remaining)
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
    port = int(os.environ.get("PORT", 5000))  # Use Render's PORT or default to 5000 locally
    app.run(host="0.0.0.0", port=port, debug=True)  # Bind to 0.0.0.0 for Render
