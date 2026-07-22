"""Offline tests for the tiny markdown renderer behind the site pages."""
import unittest

from src.web_article import md_to_html

SAMPLE = """# The Title

### The dek line

*meta · line*

---

Opening paragraph with **bold**, *italic*, `code`, and a
[link](https://example.com).

## A Section

- first bullet with **bold**
- second bullet

1. ordered one
2. ordered two

![Alt text](figures/12_playoff_race.png)

*An italic aside paragraph.*
"""


class TestRenderer(unittest.TestCase):
    def setUp(self):
        self.r = md_to_html(SAMPLE, embed_images=False)

    def test_hero_fields(self):
        self.assertEqual(self.r["title"], "The Title")
        self.assertEqual(self.r["dek"], "The dek line")
        self.assertIn("meta", self.r["meta"])

    def test_inline_formatting(self):
        b = self.r["body"]
        self.assertIn("<strong>bold</strong>", b)
        self.assertIn("<em>italic</em>", b)
        self.assertIn("<code>code</code>", b)
        self.assertIn('<a href="https://example.com">link</a>', b)

    def test_blocks(self):
        b = self.r["body"]
        self.assertIn("<h2>A Section</h2>", b)
        self.assertIn("<ul>", b)
        self.assertIn("<ol>", b)
        self.assertIn("<li>ordered one</li>", b)
        self.assertIn('src="figures/12_playoff_race.png"', b)
        self.assertIn('class="aside"', b)

    def test_lists_are_closed(self):
        b = self.r["body"]
        self.assertEqual(b.count("<ul>"), b.count("</ul>"))
        self.assertEqual(b.count("<ol>"), b.count("</ol>"))

    def test_html_is_escaped(self):
        r = md_to_html("# T\n\nA <script> tag & ampersand.",
                       embed_images=False)
        self.assertIn("&lt;script&gt;", r["body"])
        self.assertIn("&amp;", r["body"])
        self.assertNotIn("<script>", r["body"])


if __name__ == "__main__":
    unittest.main()
