from itertools import chain

import pypandoc

from peppermynt.base import Parser as _Parser


class Parser(_Parser):
    accepts = ('.md', '.markdown')

    def parse(self, markdown):
        return pypandoc.convert_text(
            markdown, 'html',
            extra_args=self.flags,
            format='markdown+smart+raw_tex+yaml_metadata_block-pipe_tables+grid_tables',
            filters=['pandoc-sidenote']
        )

    def setup(self):
        self.css_styles = [
            'tufte-css/tufte.css',
            'tufte-pandoc-css/pandoc.css',
            'tufte-pandoc-css/pandoc-solarized.css',
            'tufte-pandoc-css/tufte-extra.css',
        ]

        self.flags = [
            '--mathjax',
            '--section-divs',
            '--highlight-style=pygments',
        ] + list(chain.from_iterable(['--css', css_style] for css_style in self.css_styles))
