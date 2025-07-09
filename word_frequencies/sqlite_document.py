import sqlite3
import json
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

# Laad woordenlijst
with open("filtered_dutch_words.txt", "r", encoding="utf-8") as f:
    words = [w.strip().lower() for w in f if len(w.strip()) == 5]

# Maak database
conn = sqlite3.connect("feedback_lookup.db")
c = conn.cursor()

# Maak tabel
c.execute("DROP TABLE IF EXISTS feedback_lookup")
c.execute("""
    CREATE TABLE feedback_lookup (
        guess TEXT,
        pattern TEXT,
        target_index INTEGER
    )
""")
c.execute("CREATE INDEX idx_guess_pattern ON feedback_lookup (guess, pattern)")

# Vul tabel
for gi, guess in enumerate(words):
    print(f"Inserting: {guess}")
    for ti, target in enumerate(words):
        pattern = simulate_feedback(guess, target)
        c.execute("INSERT INTO feedback_lookup (guess, pattern, target_index) VALUES (?, ?, ?)",
                  (guess, pattern, ti))

conn.commit()
conn.close()

# Opslaan van woordenlijst
with open("words_list.json", "w", encoding="utf-8") as f:
    json.dump(words, f)

print("✅ SQLite database klaar: feedback_lookup.db + words_list.json")
