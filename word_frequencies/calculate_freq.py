from collections import Counter
from datasets import load_dataset
import re
import json
from tqdm import tqdm

# Load dataset in streaming mode
dataset = load_dataset('yhavinga/mc4_nl_cleaned', 'tiny', streaming=True)['train']

# Load your target words
with open("filtered_dutch_words.txt", encoding="utf-8") as f:
    target_words = set(word.strip().lower() for word in f)

word_counts = Counter()

# Set up tqdm progress bar (manual total, since length is unknown)
progress = tqdm(desc="Processing samples", unit="samples")

# Iterate and count
for entry in dataset:
    text = entry["text"].lower()
    words = re.findall(r"\b\w+\b", text)
    for word in words:
        if word in target_words:
            word_counts[word] += 1
    progress.update(1)

# Save the result
with open("word_frequencies.json", "w", encoding="utf-8") as f:
    json.dump(dict(word_counts), f, ensure_ascii=False, indent=2)

progress.close()
