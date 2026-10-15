# -*- coding: utf-8 -*-
"""Artist-name matching as merge.py does it (data/names.py): the spellings that are one
person, and the near-misses that must stay apart. The good merges are ones the merge
really makes (its log lists them); the false matches are what the rules were written
against.

    python3 -m unittest discover tests
"""
import os, sys, unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "data"))
from names import clean_name, fold, bare_of, toks, _toks, _vtoks, _close, _qual, resolve_variant   # noqa: E402


def resolver(*names):
    """resolve_variant over a catalogue of these names, indexed by surname as merge.py does."""
    artists = [{"n": n} for n in names]
    vsur = {}
    for j, a in enumerate(artists):
        v = _vtoks(a["n"])
        if len(v) >= 2: vsur.setdefault(v[-1], []).append(j)
    def find(name):
        j = resolve_variant(name, artists, vsur)
        return None if j is None else artists[j]["n"]
    return find


class CleanName(unittest.TestCase):
    def test_museum_damage(self):
        self.assertEqual(clean_name("' Adamson-Eric"), "Adamson-Eric")          # MuIS mononym marker
        self.assertEqual(clean_name("pseud., ' Gori"), "Gori")                  # MuIS pseudonym prefix
        self.assertEqual(clean_name("Otto  Krusten"), "Otto Krusten")           # digikogu double space
        self.assertEqual(clean_name("Gori ( Vello Agori"), "Gori (Vello Agori)")   # the dropped bracket
        self.assertEqual(clean_name("Kristjan Raud;"), "Kristjan Raud")
        self.assertEqual(clean_name(None), "")

    def test_leaves_good_names_alone(self):
        for n in ("Konrad Mägi", "Karl (jun.) Burman", "Joann Saarniit (Voldemar-Johan Saarniit)", "Navitrolla"):
            self.assertEqual(clean_name(n), n)


class Fold(unittest.TestCase):
    def test_one_name(self):
        self.assertEqual(fold("Johann Köler"), fold("Köler Johann"))           # word order
        self.assertEqual(fold("Otto Moeller"), fold("Otto Möller"))            # German oe
        self.assertEqual(fold("Ülo Sooster"), fold("ulo  sooster"))
        self.assertEqual(fold("' Adamson-Eric"), fold("Adamson-Eric"))

    def test_kept_apart(self):
        # a missing forename is a question of who, not of spelling
        self.assertNotEqual(fold("Otto Friedrich von Moeller"), fold("Otto Friedrich Theodor von Moeller"))
        # the museum declining to assert an attribution is not the attribution
        self.assertNotEqual(fold("Eugen Dücker (?)"), fold("Eugen Dücker"))
        self.assertNotEqual(fold("Johan Köler"), fold("Johann Köler"))         # that is _same_person's call, on the birth year


class Brackets(unittest.TestCase):
    def test_alias_folds(self):
        self.assertEqual(bare_of("Gori (Vello Agori)"), "Gori")
        self.assertEqual(bare_of("Aleksander Ristimägi (Eisvald)"), "Aleksander Ristimägi")

    def test_qualifier_does_not(self):
        self.assertIsNone(bare_of("Karl (jun.) Burman"))                       # father and son
        self.assertIsNone(bare_of("Karl (sen.) Burman"))
        self.assertIsNone(bare_of("Hans van der Wiele (1537 - 1612)"))          # a workshop's dates
        self.assertIsNone(bare_of("Eugen Dücker (?)"))
        self.assertIsNone(bare_of("Konrad Mägi"))


class Toks(unittest.TestCase):
    def test_exact_key(self):
        self.assertEqual(toks("Ülo Sooster"), toks("SOOSTER, Ülo"))
        self.assertEqual(toks("E. Okas"), ("okas",))                            # initials drop out
        self.assertNotEqual(toks("Evald Okas"), toks("Enn Okas"))

    def test_spelling_tokens(self):
        self.assertEqual(_toks("Carl Alexander von Winkler"), ["karl", "aleksander", "vinkler"])   # C/K, X/KS, W/V; no particle
        self.assertEqual(_toks("Henn-Olavi Roode"), ["henn", "olavi", "roode"])
        self.assertEqual(_toks("Karl (jun.) Burman"), ["karl", "burman"])
        self.assertEqual(_qual("Karl (jun.) Burman"), "jr")
        self.assertEqual(_qual("Karl Burman sr"), "sr")
        self.assertIsNone(_qual("Karl Burman"))

    def test_close(self):
        self.assertTrue(_close("johann", "johan"))
        self.assertTrue(_close("vive", "viive"))
        self.assertTrue(_close("k", "karin"))                                    # an initial
        self.assertFalse(_close("al", "ali"))                                    # too short for slack
        self.assertTrue(_close("ott", "otto"))                                   # resolve_variant asks more of a short name
        self.assertFalse(_close("maret", "margit"))


class ResolveVariant(unittest.TestCase):
    CATALOGUE = ("Woldemar Tank", "Karl Timoleon Neff", "Karl (sen.) Burman", "Karl (jun.) Burman",
                 "Vladimir Valerianovitš Bogatkin", "Aleksei Gordin", "Erich Pehap", "Ester Roode", "Piibe Arrak",
                 "Eveline von Maydell", "Carl Alexander Winkler", "Olesja Katšanovskaja-Münd", "Rauno Thomas Moss",
                 "Mare Tamm", "Otto Lepland", "Johannes Raud", "Juhan Raud", "Eduard Wiiralt", "Evald Okas")

    def setUp(self):
        self.find = resolver(*self.CATALOGUE)

    def test_good_merges(self):
        # each one the merge makes, house or gallery spelling -> the catalogue's artist
        for name, artist in [("Voldemar Tank", "Woldemar Tank"),
                             ("Carl Timoleon von Neff", "Karl Timoleon Neff"),
                             ("Karl Burman sr", "Karl (sen.) Burman"),
                             ("Karl Jr Burman", "Karl (jun.) Burman"),
                             ("Vladimir Bogatkin", "Vladimir Valerianovitš Bogatkin"),
                             ("Alexei Gordin", "Aleksei Gordin"),
                             ("Eric Pehap", "Erich Pehap"),
                             ("Esther Roode", "Ester Roode"),
                             ("Piibe-Imbi Arrak", "Piibe Arrak"),
                             ("Eveline Adelheid von Maydell", "Eveline von Maydell"),
                             ("Karl Aleksander von Winkler", "Carl Alexander Winkler"),
                             ("Olesja Münd", "Olesja Katšanovskaja-Münd"),
                             ("BRON. Eduard Wiiralt", "Eduard Wiiralt")]:      # an auction's "reserved" mark
            with self.subTest(name=name):
                self.assertEqual(self.find(name), artist)

    def test_false_matches(self):
        for name in ["Are Tamm",                    # a short given name gets no slack: Are is not Mare
                     "Ott Lepland",                 # ... nor Ott Otto
                     "Karl Burman",                 # father or son: the name does not say
                     "J. Raud",                     # an initial: Johannes or Juhan
                     "Karl Raud",
                     "Eduard Wiiralt ja Evald Okas",   # two hands are not a variant of one
                     "Eduard Wiiralt & Evald Okas",
                     "Eduard Wiiralt / Evald Okas",
                     "Eduard Wiiralti järgi",       # after Wiiralt: a copy, not his
                     "Eduard Wiiralt (?)",          # an attribution the holder would not assert
                     "Wiiralt",                     # a surname alone
                     "Evald Kangur",                # another surname
                     "Ervin Okas"]:                 # another given name
            with self.subTest(name=name):
                self.assertIsNone(self.find(name))

    def test_one_candidate_only(self):
        find = resolver("Johannes Raud", "Johannes Raud-Rätsep")
        self.assertEqual(find("Johannes Raud"), "Johannes Raud")
        find = resolver("Kristjan Raud", "Kristian Raud")                       # two close candidates: neither
        self.assertIsNone(find("Kristjan Raud"))

    def test_comma_list_is_several_people(self):
        # merge.py's log once had this list resolving to Moss
        self.assertIsNone(self.find("Ants Juske, Harry Liivrand, Rauno Thomas Moss"))


if __name__ == "__main__":
    unittest.main()
