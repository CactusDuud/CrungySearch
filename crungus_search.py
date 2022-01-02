# Project by Lintton Jiang, Miles Krick, and Sage Mahmud
# Intended for UCI CS121: Information Retrieval project

import json
import pathlib
import re
import math
import warnings

from bs4 import BeautifulSoup
from collections import defaultdict
from itertools import count
from linecache import getline
from nltk.stem import PorterStemmer
from time import time


class CrungySearchEngine:
    def __init__(self):
        self.doc_id_path = None
        self.postings = None
        self.stemmer = PorterStemmer()

    class TokenEntry:
        def __init__(self, line, source_doc=None):
            self.source_doc = source_doc
            self.doc_score = defaultdict(float)

            # Extract the postings from the line
            self.postings = line.split(', ')
            self.token = self.postings[0].split(' - ')[0]
            self.postings[0] = self.postings[0].split(' - ')[1]

        # Extract document frequencies
        # Line format: 'token - posting: occurrences, ...'
        def get_postings(self):
            self.doc_score = {int(posting.split(": ")[0]): float(posting.split(": ")[1]) for posting in self.postings}

    def process_files(self, path_to_index: pathlib.Path, doc_id_path: pathlib.Path, file_group_amount=1000):
        """
        Process files within the given path and subdirectories.
        :param doc_id_path: Path to write document IDs to
        :param path_to_index: Directory from which to create indices
        :param file_group_amount: Number of files in each index before a merge
        """
        if not path_to_index.is_dir():
            raise NotADirectoryError("Path to index given to CrungySearch is not a directory.")

        if not path_to_index.exists():
            raise NotADirectoryError("Path to index given to CrungySearch does not exist.")

        # Recreate document ID file for integrity
        doc_id_path.unlink() if doc_id_path.exists() else None
        doc_id_path.touch(exist_ok=True)
        self.doc_id_path = doc_id_path
        doc_id_line_counter = 0

        partial_token_dict = defaultdict(lambda: defaultdict(int))
        group_counter = 0
        partial_index_counter = 0

        # Read files from the given directory and do something idk I started writing this comment two weeks ago
        print("\tCreating partial indices... \n\t", end='')

        # Ignore stinky warnings IKWID
        warnings.filterwarnings("ignore", category=UserWarning, module='bs4', message='.*looks like a URL.*')
        with doc_id_path.open('a') as doc_ids:
            for folder in path_to_index.iterdir():
                for file in folder.iterdir():
                    # Get tokens from the file and store them in a temporary dict
                    with file.open() as contents:
                        file_json = json.load(contents)
                        soup = BeautifulSoup(file_json["content"], 'html.parser')
                        url = file_json["url"]

                        # Record the doc ID
                        doc_ids.write(f"{url}\n")

                        for token in re.split(r"[^0-9A-Za-z']+", soup.getText()):
                            key = self.stemmer.stem(token.replace('\'', ''))
                            partial_token_dict[key][doc_id_line_counter] += 1

                        for tag_power, tag in enumerate(['b', re.compile('^h[4-6]$'), re.compile('^h[1-3]$'), 'title']):
                            for result in soup.findAll(tag):
                                for token in re.split(r"[^0-9A-Za-z']+", str(result.string)):
                                    key = self.stemmer.stem(token.replace('\'', ''))
                                    partial_token_dict[key][doc_id_line_counter] += 2**(tag_power+1) - 1

                    doc_id_line_counter += 1
                    group_counter += 1

                    # Create a folder for partial indices if it doesn't exist
                    pathlib.Path("partial_indices").mkdir() if not pathlib.Path("partial_indices").is_dir() else None

                    # Create a partial index after reaching the max for a group
                    if group_counter >= file_group_amount:
                        print(partial_index_counter, end=', ')

                        # Delete empty key, if it exists
                        del partial_token_dict['']

                        # Write the partial index to disk
                        index_path = pathlib.Path(f"partial_indices/partial_index_{partial_index_counter}.txt")
                        with index_path.open('w') as partial_index_file:
                            for token in sorted(partial_token_dict.keys()):
                                # This writes 'term - posting: occurrences, ...' on one line
                                # Yes, it is scuffed
                                partial_index_file.write(
                                    f"{token} - " +
                                    ', '.join(
                                        [f"{k}: {v}" for k, v in sorted(partial_token_dict[token].items(),
                                                                        key=lambda _: _[1],
                                                                        reverse=True)]) +
                                    "\n")

                        # Reset temporary variables and increase partial index count
                        partial_token_dict = defaultdict(lambda: defaultdict(int))
                        group_counter = 0
                        partial_index_counter += 1
        print("\n\t...done")

    def merge_final_indices(self):
        """
        Merge the partial indices into final indices, sorted by first character
        """

        if self.doc_id_path is None:
            print("Most likely, partial indices do not exist. Please create them!")
            return

        # Count the number of docs FIXME: Pretty inefficient :(
        doc_num = 0
        with self.doc_id_path.open() as f:
            for _ in f:
                doc_num += 1

        # Make a folder  for the final indices if it doesn't already exist
        pathlib.Path("final_indices").mkdir() if not pathlib.Path("final_indices").is_dir() else None

        partial_index_files = [_.open() for _ in pathlib.Path("partial_indices").iterdir()]
        index_char = ''
        final_index_file = None

        # Get the first "entry" of each partial index, along with the fd number and the list of frequencies
        try:
            entries = [self.TokenEntry(_.readline(), source_doc=_) for _ in partial_index_files]
            for e in entries:
                e.get_postings()

            # While there are still more entries to add, find the highest lexicographical entry, merge the frequencies
            # found, and add them to the final_index
            while entries:
                # Sort entries for easier processing
                sorted_entries = sorted(entries, key=lambda _: _.token)

                # List of files that will need to be pulled from at the end of this iteration
                to_pull = [sorted_entries[0].source_doc]
                pending_token = sorted_entries[0].token
                pending_token_dict = defaultdict(float)
                for url_id in sorted_entries[0].doc_score.keys():
                    pending_token_dict[url_id] += sorted_entries[0].doc_score[url_id]

                # Merge duplicate entries
                last_valid_index = 1
                for entry in sorted_entries[1:]:
                    if entry.token > pending_token:
                        break
                    for url_id in entry.doc_score.keys():
                        pending_token_dict[url_id] += entry.doc_score[url_id]
                    to_pull.append(entry.source_doc)
                    last_valid_index += 1

                entries = [e for e in entries if e.token != pending_token]

                # Ensure this is written to the correct sub-index
                if index_char < pending_token[0]:
                    final_index_file.close() if final_index_file is not None else None

                    index_char = pending_token[0]
                    final_path = pathlib.Path(f"final_indices/final_index_{index_char}.txt")
                    try:
                        final_index_file = open(final_path, "w")
                        print(f"\tWriting {final_path.name}...")
                    except IOError:
                        print(f"\tCould not open new file {final_path.name}")
                        return

                # Update pending token dict with weights instead of counts
                for k in pending_token_dict:
                    pending_token_dict[k] = self.calculate_weight(int(pending_token_dict[k]),
                                                                  len(pending_token_dict.keys()),
                                                                  doc_num)

                # Write to final index in same format as partial indices
                final_index_file.write(
                    f"{pending_token} - " +
                    ', '.join(
                        [f"{k}: {v:.3f}" for k, v in sorted(pending_token_dict.items(),
                                                            key=lambda _: _[1],
                                                            reverse=True)]) +
                    "\n")

                # Pull a new line from files used FIXME: lol this ain't the best solution
                try:
                    entries += [self.TokenEntry(_.readline(), source_doc=_) for _ in to_pull]
                    for e in entries:
                        e.get_postings()
                except IndexError:
                    pass
        finally:
            for f in partial_index_files:
                f.close()
            final_index_file.close() if final_index_file is not None else None

        # Delete partial indices once they are used
        for partial_index in pathlib.Path("partial_indices").iterdir():
            partial_index.unlink(missing_ok=True)

    @staticmethod
    def calculate_weight(term_freq: int, doc_freq: int, total_docs: int) -> float:
        """
        Calculate the tf-idf weight of a document in the inverted index.

        :param term_freq: Frequency of the term
        :param doc_freq: Frequency of documents with the term
        :param total_docs: Total number of documents
        :return: tf-idf score
        """
        if term_freq < 0:
            return 0
        tf_weight = 1 + math.log(term_freq, 10)
        idf = math.log(total_docs / doc_freq, 10)
        return tf_weight * idf

    def process_query(self, query: str, num_to_retrieve: int):
        query_start_time = time()

        # Handle blank queries
        if query == "":
            print(f"Your query was empty! (found in {time() - query_start_time:.3f}s)")
            return

        # Split query into terms
        query_terms = [term.replace('\'', '') for term in re.split(r"[^0-9A-Za-z']+", query)]
        search_results = []

        # Search final indices for the query
        for term in query_terms:
            stemmed_term = self.stemmer.stem(term.strip().lower().replace('\'', ''))
            index_char = stemmed_term[0]
            index_path = pathlib.Path(f"final_indices/final_index_{index_char}.txt")

            # Open the relevant index and read each line for the entry in question
            with open(index_path, "r") as index_file:
                term_in_index = False
                for line in index_file:
                    entry = self.TokenEntry(line)
                    if entry.token == stemmed_term:
                        entry.get_postings()
                        search_results.append(entry)
                        term_in_index = True
                        break

            if not term_in_index:
                print(f"No documents contain the term \"{term}\"")

        # Print the results of the search
        if search_results:

            document_results, num_results = self.and_results(search_results)

            if num_results == 0:
                print(f"Your query has no results (found in {time() - query_start_time:.3f}s)")
            else:
                print(f"\tFound in {time() - query_start_time:.3f}s")
                page_count = 0
                # Iterate through results in pages (while whole document_results can be generated)
                for i in range(num_results // num_to_retrieve):
                    # Iterate through docs on page and print them to console
                    page = [next(document_results) for _ in range(num_to_retrieve)]
                    for doc in page:
                        doc_name = getline(self.doc_id_path.name, doc[0] + 1)
                        print(f"{page_count + 1}. {doc_name} \t(Score: {doc[1]:.3f})")
                        page_count += 1
                    print(f"Showing results {result_display_num * i + 1} - {result_display_num * (i + 1)} "
                          f"of {num_results} results")

                    # Query the user for more pages
                    stop_query = False
                    for _ in count(0):
                        print_more_pages = input(f"Show the next {result_display_num} pages? y/n: ").strip().lower()
                        if print_more_pages == 'y':
                            # Proceed for non-final pages
                            if num_results - result_display_num * (i + 1) >= result_display_num:
                                break

                            # Special case for the final page
                            page = tuple(document_results)
                            for doc in page:
                                doc_name = getline(self.doc_id_path.name, doc[0] + 1)
                                print(f"{page_count + 1}. {doc_name} \t(Score: {doc[1]:.3f})")
                                page_count += 1
                            print(
                                f"Showing {result_display_num * (i + 1) + 1} - {num_results} of {num_results} results")
                        else:
                            stop_query = True
                        break
                    if stop_query:
                        break

                # Special case for only one page of results
                if num_results // num_to_retrieve == 0:
                    page = tuple(document_results)
                    for doc in page:
                        doc_name = getline(self.doc_id_path.name, doc[0] + 1)
                        print(f"{page_count + 1}. {doc_name} \t(Score: {doc[1]:.3f})")
                        page_count += 1
                    print(f"Showing {1 if num_results else 0} - {num_results} of {num_results} results")

        else:
            print(f"Your query has no results (found in {time() - query_start_time:.3f}s)")

    @staticmethod
    def result_generator(matches: [dict]) -> [dict]:
        """
        Yield documents sorted by relevance
        :param matches: Unsorted documents
        :return: Documents sorted by relevance
        """
        sorted_matches = sorted(matches.items(), key=lambda _: _[1], reverse=True)
        yield from sorted_matches

    def and_results(self, search_results) -> ([int], int):
        """
        Given search results from query, return the documents sorted by their relevance
        :param search_results: The raw search result entries (guaranteed to be at least 1 entry)
        :return: Generator of urls (by docID) sorted by their relevance
        """

        # Handle one result
        if len(search_results) == 1:
            return self.result_generator(search_results[0].doc_score), len(search_results[0].doc_score)

        # Sort the terms by the number of their occurrences in the document
        sorted_terms = sorted(search_results, key=lambda _: len(_.doc_score))
        matched_docs = defaultdict(float)

        # Pick the first doc as the comparison point
        for doc in sorted_terms[0].doc_score.keys():
            # If every entry occurs in this doc, add the total score to matched pages
            if all(doc in token.doc_score for token in sorted_terms[1:]):
                total_score = sum(token.doc_score[doc] for token in sorted_terms[1:])
                if total_score > 0:
                    matched_docs[doc] = total_score

        return self.result_generator(matched_docs), len(matched_docs)


if __name__ == '__main__':
    engine = CrungySearchEngine()

    dir_path = pathlib.Path("DEV")
    if not dir_path.exists():
        print("WARN: No ~/DEV file directory found, please define a path with the --setdir command")

    # Check if indices need to be remade
    doc_id_file = pathlib.Path("docID.txt")
    if not doc_id_file.exists():
        print("WARN: No document ID file found, it's recommended to rebuild indices.")
    else:
        engine.doc_id_path = doc_id_file

    # Main loop
    result_display_num = 5
    print(f"\n\n"
          f"Welcome to CrungySearch, the crungiest of search engines!\n"
          f"Enter your search query to find the {result_display_num} most relevant results.\n"
          f"Type \'--h\' for help.\n")
    for _ in count(0):
        user_query = input("Search for: ").strip().lower()
        if user_query == "--h":
            print("CrungySearch commands:\n\n"
                  "\t--setdir\tSet a new directory to build indices from (default ~/DEV)\n\n"
                  "\t--rpi   \tRebuilds only partial indices.\n"
                  "\t--rfi   \tRebuilds only final indices. Assumes partial indices exist.\n"
                  "\t--ri    \tRebuilds first partial and then final indices.\n\n"
                  "\t--h     \tShows CrungySearch commands.\n"
                  "\t--q     \tQuits CrungySearch.\n\n")

        elif user_query == '--q':
            print("Thank you for using CrungySearch!\n"
                  "Have a crungy day!")
            break

        elif user_query == "--setdir":
            # Define a new path to construct indices from
            user_input = input("Please specify a new path to create indices from: ").strip()
            dir_path = pathlib.Path(user_input)
            while not dir_path.exists() or user_input == '':
                print("Invalid path")
                user_input = input("Please specify a new path to create indices from: ").strip()
                dir_path = pathlib.Path(user_input)

        elif user_query == "--rpi":
            partial_indexing_start_time = time()
            engine.process_files(dir_path, doc_id_file)
            print(f"\tPartial indexing executed in "
                  f"{int((time() - partial_indexing_start_time) // 60)}m "
                  f"{(time() - partial_indexing_start_time) % 60:.3f}s\n"
                  f"\tDocument IDs were written to \"{doc_id_file.name}\"")

        elif user_query == "--rfi":
            final_indexing_start_time = time()
            engine.merge_final_indices()
            print(f"\tIndex merging executed in "
                  f"{int((time() - final_indexing_start_time) // 60)}m "
                  f"{(time() - final_indexing_start_time) % 60:.3f}s")

        elif user_query == "--ri":
            partial_indexing_start_time = time()
            engine.process_files(dir_path, doc_id_file)
            print(f"\tPartial indexing executed in "
                  f"{int((time() - partial_indexing_start_time) // 60)}m "
                  f"{(time() - partial_indexing_start_time) % 60:.3f}s\n"
                  f"\tDocument IDs were written to \"{doc_id_file.name}\"")

            final_indexing_start_time = time()
            engine.merge_final_indices()
            print(f"\tIndex merging executed in "
                  f"{int((time() - final_indexing_start_time) // 60)}m "
                  f"{(time() - final_indexing_start_time) % 60:.3f}s")

        else:
            engine.process_query(user_query, result_display_num)
            if user_query:
                print(f"Search for \"{user_query}\" complete!\n")
            else:
                print(f"Search for nothing complete!\n")
