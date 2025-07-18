import json
import math
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from tqdm import tqdm

# --- Load word list ---
with open("filtered_dutch_words.txt", "r", encoding="utf-8") as f:
    all_words = [line.strip().lower() for line in f if len(line.strip()) == 5]

with open("word_frequencies.json", encoding="utf-8") as f:
    word_freqs = json.load(f)


# --- Old entropy calculation ---
def calculate_entropy(possible_words):
    letter_positions = [{} for _ in range(5)]
    for word in possible_words:
        for i, letter in enumerate(word):
            letter_positions[i][letter] = letter_positions[i].get(letter, 0) + 1

    entropy_scores = {}
    for word in possible_words:
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

# --- Frequency fallback ---
def find_occurence(possible_words):
    return {word: word_freqs.get(word.lower(), 0) for word in possible_words}


# --- Feedback generation (Wordle-style) ---
def get_feedback(guess, target):
    feedback = [''] * 5
    target_chars = list(target)
    for i in range(5):
        if guess[i] == target[i]:
            feedback[i] = 'G'
            target_chars[i] = None
    for i in range(5):
        if feedback[i]:
            continue
        if guess[i] in target_chars:
            feedback[i] = 'Y'
            target_chars[target_chars.index(guess[i])] = None
        else:
            feedback[i] = 'B'
    return ''.join(feedback)


# --- Filtering logic (old version) ---
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


# --- Simulation logic ---
def simulate_old_bot(args):
    target_word, cutoff = args
    remaining = all_words.copy()

    for turn in range(1, 8):
        if not remaining:
            return 7

        if len(remaining) == 1:
            guess = remaining[0]
        elif 1 < len(remaining) <= cutoff:
            scores = find_occurence(remaining)
            guess = max(scores, key=scores.get)
        else:
            scores = calculate_entropy(remaining)
            guess = max(scores, key=scores.get)

        if guess == target_word:
            return turn

        feedback = get_feedback(guess, target_word)
        remaining = filter_words(guess, feedback, remaining)

    return 7  # Too many turns


# --- Benchmark wrapper ---
def run_benchmark_old_bot(cutoff=7, top_n=len(all_words)):
    test_words = sorted(all_words, key=lambda w: word_freqs.get(w, 0), reverse=True)[:top_n]
    args = [(word, cutoff) for word in test_words]

    with ProcessPoolExecutor() as executor:
        scores = list(tqdm(executor.map(simulate_old_bot, args),
                           total=len(test_words),
                           desc=f"[OLD BOT] Cutoff={cutoff}, Top {top_n}"))

    avg_score = sum(scores) / len(scores)
    return {
        "cutoff": cutoff,
        "top_n": top_n,
        "average_score": round(avg_score, 3),
        "distribution": {i: scores.count(i) for i in range(1, 8)}
    }


# --- Run if main ---
if __name__ == "__main__":
    result = run_benchmark_old_bot(cutoff=1)

    print(f"\n[OLD BOT] Benchmark Result (cutoff={result['cutoff']}, top_n={result['top_n']}):")
    print(f"  Average score: {result['average_score']}")
    print(f"  Distribution: {result['distribution']}")
