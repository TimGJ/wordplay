"""
Playing around with wordlist
"""

import argparse
import re
import collections
import pathlib
import logging
import itertools
import json
import sys


class Wordle:
    """
    Simple class to represent the number of letters in the same position in a word and the
    number which are common but not in the right position.
    """

    def __init__(self):
        self.position = 0
        self.common = 0

    def __repr__(self):
        return f"({self.position:,}/{self.common:,})"

    def asDict(self):
        return {"position": self.position, "common": self.common}


class Word:
    """
    A word from the list
    """
    def __init__(self, word):
        assert isinstance(word, str), "Word must be a string"
        self.original = word
        self.word = word.lower()
        self.length = len(self.word)
        self.acronym = word.isupper()
        self.proper = True if not self.acronym and word[0].isupper() else False
        self.palindrome = self.word == self.word[::-1]
        self.counts = collections.Counter(self.word)
        self.anagrams = []
        self.subwords = []
        self.wordle = Wordle()

    def __len__(self):
        return self.length

    def __repr__(self):
        return f"Word('{self.word}')"

    def isAnagram(self, other):
        """
        Are self and other anagrams of each other?
        :param other:
        :return: boolean
        """
        return self.counts == other.counts

    def isSubword(self, other):
        """
        Are all the letters of other present in self
        :param other:
        :return: boolean
        """
        return all(self.counts[letter] >= other.counts[letter] for letter in other.counts)

    def wordleScore(self, other):
        """
        Works out how many letters are in the same position in other and how many of the remainder
        match but are not in the correct position. Only works on words of the same length.
        :param other:
        :return: None
        """
        if len(self) == len(other):
            self.wordle.position += sum(1 for i in range(len(self.word)) if self.word[i] == other.word[i])
            self.wordle.common += sum(min(self.counts[letter], other.counts[letter]) for letter in self.counts)
    def asDict(self):
        return {
            "original": self.original,
            "word": self.word,
            "proper": self.proper,
            "palindrome": self.palindrome,
            "counts": dict(self.counts),
            "anagrams": [token.word for token in self.anagrams],
            "subwords": [token.word for token in self.anagrams],
            "wordle": self.wordle.asDict(),
        }

class WordList:
    """
    WordList is (basically) a wrapper round a series of dictionaries of Word objects with some additional methods
    """

    def __init__(self, source, minlen=3, pagination=1_000_000):
        wordre = re.compile("^[a-zA-Z]{"+str(minlen)+",}$")

        self.source = source
        self.wordpath = pathlib.Path(source)
        if not (self.wordpath.exists() and self.wordpath.is_file()):
            raise FileNotFoundError(f"File not found: {source}")
        self.words = {line: Word(line) for line in self.wordpath.read_text().splitlines() if wordre.match(line)}
        self.bins = collections.defaultdict(dict)
        for word in self.words.values():
            self.bins[word.length][word.word] = word
        logging.debug(f"Read {len(self.words):,} words from {self.wordpath.name}")

        for l in sorted(self.bins.keys()):
            logging.info(f"Processing {len(self.bins[l]):,} words of {l} characters")
            for i, (a, b) in enumerate(itertools.combinations(self.bins[l].values(), 2), 1):
                if i % pagination == 0:
                    logging.debug(f"[{l}] {i:,} {a.word} : {b.word}")
                if a.isAnagram(b):
                    a.anagrams.append(b)
                    b.anagrams.append(a)
                a.wordleScore(b)
                b.wordleScore(a)

    def __repr__(self):
        return f"WordList({self.source} ({len(self.words):,} words)"

    def asDict(self):
        return {word: value.asDict() for word, value in self.words.items()}
if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Playing with words")
    ap.add_argument("-v", "--verbose", action="count", default=0, help="Increase verbosity")
    ap.add_argument("-o", "--output", help="Output JSON filename", default="words.json", type=str)
    ap.add_argument("source", help="Source word list")
    args = ap.parse_args()
    levels = [logging.WARNING, logging.INFO, logging.DEBUG]
    logging.basicConfig(level=levels[min(args.verbose, len(levels)-1)],
                        format="%(asctime)s %(levelname)s %(message)s")
    try:
        words = WordList(args.source)
        with open(args.output, "w") as outfile:
            logging.debug(f"Writing to {args.output}")
            json.dump(words.asDict(), outfile, indent=4)
    except FileNotFoundError:
        print(f"File not found: {args.source}")
        sys.exit(0)
    except KeyboardInterrupt:
        print("Interrupted")
    finally:
        logging.info("Done")
