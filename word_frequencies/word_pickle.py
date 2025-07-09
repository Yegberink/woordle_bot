import json
import pickle
from collections import defaultdict
from array import array

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

word_to_index = {w: i for i, w in enumerate(words)}

# Build optimized lookup
feedback_lookup = {}
for guess in words:
    patterns = defaultdict(list)
    for idx, target in enumerate(words):
        pattern = simulate_feedback(guess, target)
        patterns[pattern].append(idx)

    # Convert to compact structure: arrays
    compact_patterns = {p: array('H', idxs) for p, idxs in patterns.items()}
    feedback_lookup[guess] = compact_patterns

# Save compact pickle
with open('feedback_lookup.pkl', 'wb') as pkl_file:
    pickle.dump({'words': words, 'lookup': feedback_lookup}, pkl_file, protocol=pickle.HIGHEST_PROTOCOL)

print("✅ Compacte pickle opgeslagen (feedback_lookup.pkl)")
