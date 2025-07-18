import json
import math
import pickle
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from tqdm import tqdm

# --- Load data ---
with open("filtered_dutch_words.txt", "r", encoding="utf-8") as f:
    all_words = [w.strip().lower() for w in f if len(w.strip()) == 5]

with open("word_frequencies.json", "r", encoding="utf-8") as f:
    word_freqs = json.load(f)

with open("feedback_lookup.pkl", "rb") as pkl_file:
    data = pickle.load(pkl_file)

words_list = data['words']
feedback_lookup = data['lookup']
word_to_index = {w: i for i, w in enumerate(words_list)}

# --- Cache target sets for fast lookup ---
cached_lookup_sets = {
    guess: {pattern: set(indices) for pattern, indices in patterns.items()}
    for guess, patterns in feedback_lookup.items()
}

def simulate_target_word(args):
    word, cutoff = args
    return run_single_simulation(word, cutoff=cutoff)

# --- Feedback helper ---
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

# --- Word filtering logic ---
def filter_words(guess, feedback, words):
    filtered = []
    min_counts = {}
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

        for g, f in zip(guess, feedback):
            if f == "B" and min_counts.get(g, 0) == 0 and g in w:
                ok = False
                break

        if ok:
            filtered.append(w)
    return filtered

# --- Entropy calculation ---
def calculate_entropy(remaining, guess_words):
    total = len(remaining)
    remaining_indices = {word_to_index[w] for w in remaining}
    entropy_scores = {}

    for guess in guess_words:
        entropy = 0.0
        pattern_map = cached_lookup_sets.get(guess, {})
        for target_indices in pattern_map.values():
            cnt = len(remaining_indices & target_indices)
            if cnt == 0:
                continue
            p = cnt / total
            entropy -= p * math.log2(p)
        entropy_scores[guess] = entropy

    return entropy_scores

# --- Simulate single game ---
def run_single_simulation(target_word, cutoff=5):
    remaining = all_words.copy()
    history = []

    for turn in range(1, 8):  # Max 7 turns
        if not remaining:
            return 7  # Treat as failure

        if len(remaining) <= cutoff:
            candidates = sorted(remaining, key=lambda w: word_freqs.get(w, 0), reverse=True)
        else:
            entropy_scores = calculate_entropy(remaining, all_words)
            candidates = sorted(entropy_scores.items(), key=lambda x: x[1], reverse=True)
            candidates = [c[0] for c in candidates]

        guess = candidates[0]
        history.append(guess)

        if guess == target_word:
            return turn

        feedback = get_feedback(guess, target_word)
        remaining = filter_words(guess, feedback, remaining)

    return 7  # Penalize anything >6 turns

# --- Parallel benchmark ---
def run_benchmark_parallel(cutoff=5, top_n=len(all_words)):
    test_words = sorted(all_words, key=lambda w: word_freqs.get(w, 0), reverse=True)[:top_n]
    inputs = [(word, cutoff) for word in test_words]

    with ProcessPoolExecutor() as executor:
        scores = list(tqdm(executor.map(simulate_target_word, inputs),
                           total=len(inputs),
                           desc=f"Cutoff={cutoff}, Top {top_n}"))

    average_score = sum(scores) / len(scores)
    return {
        "cutoff": cutoff,
        "top_n": top_n,
        "average_score": round(average_score, 3),
        "distribution": {i: scores.count(i) for i in range(1, 8)}
    }


# --- Entry point ---
if __name__ == "__main__":
    # Example: test with cutoff=5, using top 500 words
    result = run_benchmark_parallel(cutoff=1)
    print(f"\nBenchmark Result (cutoff={result['cutoff']}, top_n={result['top_n']}):")
    print(f"  Average score: {result['average_score']}")
    print(f"  Distribution: {result['distribution']}")
