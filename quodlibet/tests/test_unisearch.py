# -*- coding: utf-8 -*-
# Copyright 2014 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

import re
import unicodedata

from tests import TestCase

from quodlibet.unisearch import re_add_variants
from quodlibet.unisearch.db import diacritic_for_letters
from quodlibet.unisearch.parser import re_replace_literals


class TUniSearch(TestCase):

    def test_mapping(self):
        cache = diacritic_for_letters(False)
        new = diacritic_for_letters(True)
        self.assertEqual(sorted(cache.items()), sorted(new.items()))

    def test_normalize_input(self):
        assert re.match(
            re_add_variants(unicodedata.normalize("NFD", u"ö")), u"ö")

    def test_re_replace(self):
        r = re_add_variants(u"aa")
        self.assertTrue(u"[" in r and u"]" in r and r.count(u"ä") == 2)

    def test_re_replace_multi(self):
        r = re_add_variants(u"ae")
        self.assertEqual(r, u"(?:[aàáâãäåāăąǎǟǡǻȁȃȧḁạảấầẩẫậắằẳẵặ]"
                            u"[eèéêëēĕėęěȅȇȩḕḗḙḛḝẹẻẽếềểễệ]|[æǣǽ])")

        r = re_add_variants(u"SS")
        self.assertEqual(r, u"(?:[SŚŜŞŠȘṠṢṤṦṨꞄ][SŚŜŞŠȘṠṢṤṦṨꞄ]|ẞ)")

        r = re_add_variants(u"ss")
        self.assertEqual(r, u"(?:[sśŝşšșṡṣṥṧṩꞅ][sśŝşšșṡṣṥṧṩꞅ]|ß)")

    def test_punct(self):
        r = re_add_variants(u"'")
        assert "`" in r
        assert "'" in r
        r = re_add_variants(u"''")
        assert "\"" in r
        r = re_add_variants(u'"')
        assert "”" in r
        assert "“" in r
        r = re_add_variants(u'\\*')
        assert re.match(r, "*")

    def test_re_replace_multi_fixme(self):
        # we don't handler overlapping sequences, so this doesn't match "LỺ"
        r = re_add_variants(u"LLL")
        self.assertEqual(r, u"(?:[LĹĻĽḶḸḺḼŁ][LĹĻĽḶḸḺḼŁ]|Ỻ)[LĹĻĽḶḸḺḼŁ]")

    def test_re_replace_multi_nested(self):
        r = re_add_variants(u"(եւ)")
        self.assertEqual(r, u"((?:եւ|և))")
        r = re_add_variants(u"(եւ)+")
        self.assertEqual(r, u"((?:եւ|և))+")

    def test_re_replace_escape(self):
        r = re_add_variants(u"n\\n")
        self.assertEqual(r, u"[nñńņňǹṅṇṉṋŉ]\n")

    def test_construct_regexp(self):
        res = [
            (u"\\.", None),
            (u"..", None),
            (u"\\.", None),
            (u"^a\aa[ha-z]k{1,3}h*h+h?(x|yy)(a+b|cd)$", None),
            (u"(?=Asimov)", None),
            (u"(?!Asimov)", None),
            (u"(?<=abc)def", None),
            (u"(?<!foo)", None),
            (u"(?:foo)", None),
            (u"(?#foo)", u""),
            (u"(.+) \1", None),
            (u"\\A\\b\\B\\d\\D\\s\\S\\w\\W\\Z\a",
             u"\\A\\b\\B[\\d][\\D][\\s][\\S][\\w][\\W]\\Z\a"),
            (u"a{3,5}?a+?a*?a??", None),
            (u"^foo$", None),
            (u"[-+]?(\\d+(\\.\\d*)?|\\.\\d+)([eE][-+]?\\d+)?",
             u"[\\-\\+]?([\\d]+(\\.[\\d]*)?|\\.[\\d]+)([eE][\\-\\+]?[\\d]+)?"),
            (u"(\$\d*)", u"(\\$[\\d]*)"),
            (u"\\$\\.\\^\\[\\]\\:\\-\\+\\?\\\\", None),
            (u"[^a][^ab]", None),
            (u"[ab][abc]", None),
            (u"[.]", u"\\."),
            (u"[^a-z]", None),
            (u"[^a-z\w]", None),
        ]

        for r, o in res:
            if o is None:
                o = r
            self.assertEqual(re_replace_literals(r, {}), o)

    def test_construct_regexp_broken(self):
        self.assertRaises(re.error, re_replace_literals, u"[", {})
        self.assertRaises(NotImplementedError,
                          re_replace_literals,
                          u"(?P<quote>['\"]).*?(?P=quote)", {})

    def test_seq(self):
        assert re_add_variants(u"[x-y]") == u"[ẋẍýÿŷȳẏẙỳỵỷỹx-y]"
        assert re_add_variants(u"[f-gm]") == u"[ḟꝼĝğġģǧǵḡᵹf-gmḿṁṃ]"
        assert re_add_variants(u"[^m]") == u"[^mḿṁṃ]"
        assert re_add_variants(u"[^m-m\w]") == u"[^ḿṁṃm-m\w]"
        assert re_add_variants(u"[^m-m]") == "[^ḿṁṃm-m]"
        assert re_add_variants(u"[^ö]") == u"[^ö]"
        assert re_add_variants(u"[LLL]") == u"[LĹĻĽḶḸḺḼŁ]"

    def test_literal(self):
        assert re_add_variants(u"f") == u"[fḟꝼ]"
        assert u"ø" in re_add_variants(u"o")
        assert u"Ø" in re_add_variants(u"O")
        assert re_add_variants(u"[^f]") == u"[^fḟꝼ]"