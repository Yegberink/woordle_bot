# Precompute feedback patterns for Wordle solver
import json
import pickle
from collections import defaultdict

def simulate_feedback(guess, target):
    result = ['B'] * 5
    target_letters = list(target)
    for i in range(5):
        if guess[i] == target[i]:
            result[i] = 'G'
            target_letters[i] = None
    for i in range(5):
        if result[i] == 'B' and guess[i] in target_letters:
            result[i] = 'Y'
            target_letters[target_letters.index(guess[i])] = None
    return ''.join(result)

# Load word list
with open('filtered_dutch_words.txt', 'r', encoding='utf-8') as f:
    words = [w.strip().lower() for w in f if len(w.strip()) == 5]

# Build lookup: for each guess, map patterns to list of target indices
feedback_lookup = {}
for guess in words:
    patterns = defaultdict(list)
    for idx, target in enumerate(words):
        pattern = simulate_feedback(guess, target)
        patterns[pattern].append(idx)
    feedback_lookup[guess] = dict(patterns)

# Save lookup to pickle
with open('feedback_lookup.pkl', 'wb') as pkl_file:
    pickle.dump({'words': words, 'lookup': feedback_lookup}, pkl_file)

# Also save index mapping for JSON use if needed
with open('feedback_lookup_meta.json', 'w', encoding='utf-8') as meta_file:
    json.dump({'words': words}, meta_file)

print('Precompute complete: feedback_lookup.pkl and meta saved')
