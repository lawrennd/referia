"""MathJax typesetting support for the web review page.

Jupyter Markdown widgets use ipywidgets.HTMLMath, so ``$...$`` in
``_referia.yml`` typesets in the notebook.  The web backend must leave those
delimiters in the HTML and load MathJax on the page shell.
"""

from referia.web.render import render_widget


class TestTexDelimitersSurviveRender:
    def test_html_math_keeps_tex_delimiters(self):
        html = render_widget(
            {"type": "HTMLMath", "field": "", "args": {"value": r"Area $A(c)$ of $y=x+c$."}}
        )
        assert "$A(c)$" in html
        assert "$y=x+c$" in html

    def test_markdown_keeps_tex_delimiters(self):
        """python-markdown must leave $...$ intact for MathJax on the page."""
        html = render_widget({
            "type": "Markdown",
            "field": "",
            "args": {
                "value": r"vertices $(0, 0)$ and the line $y=x+c$. Area $A(c)$.",
            },
        })
        assert "$(0, 0)$" in html
        assert "$y=x+c$" in html
        assert "$A(c)$" in html
