# Script by Sage Mahmud (#11686625) for Prof. Lopes' Information Retrieval class

import re
import sys
from collections import defaultdict
from pathlib import Path


class Tokenizer:

    def __init__(self, corpus_path: Path):
        self.corpus = corpus_path
        self.tokens = []
        self.token_freq = defaultdict(int)

    def tokenize(self) -> [str]:
        """
        Reads a text file and returns a list of the tokens in that file. A token is a sequence of alphanumeric
        characters, independent of capitalization.

        This function is polynomial in worst-case runtime (nested loops).

        :return: List of tokens as strings (modifies self.tokens)
        """
        with self.corpus.open('r', encoding="utf8") as text:
            for line in text:
                for token in re.compile(r"[a-zA-Z0-9']{3,}").findall(line):
                    self.tokens.append(token.lower())

        return self.tokens

    def compute_word_frequencies(self) -> {str: int}:
        """
        Counts the number of occurrences of each token in the token list.

        This function is polynomial in worst-case runtime (inserting into a hash is at worst n, which is done n times).

        :return: Dict of tokens as strings to their frequency as ints (modifies self.token_freq)
        """
        if not self.tokens:
            print("Call tokenize first to generate tokens.")
            return

        token_map = defaultdict(int)
        for token in self.tokens:
            token_map[token] += 1

        self.token_freq = token_map
        return self.token_freq

    def print_frequencies(self):
        """
        Prints out the word frequency count onto the screen.

        This function is polynomial in worst-case runtime.
        """
        if not self.token_freq:
            print("Call compute_word_frequencies first to generate frequencies.")
            return

        for key, value in sorted(self.token_freq.items(), key=lambda e: e[1], reverse=True):
            print(f"{key} - {value}")

    def write_frequencies(self, dump_file: str, key, reverse):
        """
        Writes the word frequency count to a file
        """
        with open(dump_file, mode='w') as file:
            for k, v in sorted(self.token_freq.items(), key=key, reverse=reverse):
                file.write(f"{k} - {v}\n")


if __name__ == '__main__':
    corpus_path = Path(sys.argv[1])
    if corpus_path.exists():
        print(f"Tokenizing {corpus_path}")
        tokenizer = Tokenizer(corpus_path)
        tokenizer.tokenize()
        tokenizer.compute_word_frequencies()
        # tokenizer.print_frequencies()
        tokenizer.write_frequencies("word_counts.txt", key=lambda e: e[1], reverse=True)
    else:
        print(f"ERROR: File \'{corpus_path}\' does not exist.")
