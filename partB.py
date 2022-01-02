# Script by Sage Mahmud (#11686625) for Prof. Lopes' Information Retrieval class

import sys
from pathlib import Path

from partA import Tokenizer


def print_common(path1: Path, path2: Path, print_words=False):
    """
    Takes two paths to text files and prints the number of words they have in common.

    This function is linear in worst-case runtime.

    :param path1: A Path leading to the first text file
    :param path2: A Path leading to the second text file
    """

    # Tokens for the first corpus
    tokenizer1 = Tokenizer(path1)
    tokenizer1.tokenize()
    tokenizer1.compute_word_frequencies()

    # Tokens for the second corpus
    tokenizer2 = Tokenizer(path2)
    tokenizer2.tokenize()
    tokenizer2.compute_word_frequencies()

    common_tokens = set(tokenizer1.tokens) & set(tokenizer2.tokens)
    None if not print_words else print(common_tokens)
    print(len(common_tokens))


if __name__ == '__main__':
    corpus1_path = Path(sys.argv[1])
    corpus2_path = Path(sys.argv[2])
    print_words = bool(sys.argv[3]) if len(sys.argv) > 3 else False
    if corpus1_path.exists() and corpus2_path.exists():
        print_common(corpus1_path, corpus2_path, print_words)
    else:
        if not corpus1_path.exists():
            print(f"ERROR: File \'{corpus1_path}\' does not exist.")
        if not corpus2_path.exists():
            print(f"ERROR: File \'{corpus2_path}\' does not exist.")
