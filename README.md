# woordle bot

In this repository is the code for a bot that gives the "best" possible guess for a Dutch wordle (woordle) based on reducing entropy. The list of Dutch five letter words is based on the Opentaal word list basiswoorden-gekeurd (https://github.com/OpenTaal/opentaal-wordlist). When the list of words is reduced to five of less, the guess is no longer based on reducing entropy but on the highest occurence of the remaining words in the Dutch mC4 tiny dataset (https://huggingface.co/datasets/yhavinga/mc4_nl_cleaned).
