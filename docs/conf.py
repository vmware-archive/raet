# coding: utf-8
# pylint: disable=C0103,W0622
'''
Sphinx documentation for Raet
'''
import sys
import os

from sphinx.directives import TocTree

# pylint: disable=R0903
class Mock(object):
    '''
    Mock out specified imports

    This allows autodoc to do it's thing without having oodles of req'd
    installed libs. This doesn't work with ``import *`` imports.

    http://read-the-docs.readthedocs.org/en/latest/faq.html#i-get-import-errors-on-libraries-that-depend-on-c-modules
    '''
    def __init__(self, *args, **kwargs):
        pass

    def __call__(self, *args, **kwargs):
        return Mock()

    @classmethod
    def __getattr__(self, name):
        if name in ('__file__', '__path__'):
            return '/dev/null'
        else:
            return Mock()
# pylint: enable=R0903

MOCK_MODULES = [
    'importlib',
]

for mod_name in MOCK_MODULES:
    sys.modules[mod_name] = Mock()

### Add a few directories to the Python path
try:
    docs_basepath = os.path.abspath(os.path.dirname(__file__))
except NameError:
    # sphinx-intl and six execute some code which will raise this NameError
    # assume we're in the doc/ directory
    docs_basepath = os.path.abspath(os.path.dirname('.'))

addtl_paths = (
    os.pardir,  # raet itself (for autodoc)
    '_ext',  # custom Sphinx extensions
)

for path in addtl_paths:
    sys.path.insert(0, os.path.abspath(os.path.join(docs_basepath, path)))

# We're now able to import raet
from raet import __version__

project = 'Raet'
document_title = 'Raet Documentation'
copyright = '2014 SaltStack, Inc.'
author = ['SaltStack, Inc.']

master_doc = 'index'

version = __version__
release = version

language = 'en'
locale_dirs = [
    '_locale',
]
gettext_compact = False

extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.autosummary',
    'sphinx.ext.intersphinx',
]

intersphinx_mapping = {
    'salt': ('http://docs.saltstack.com/en/latest/', None),
}


### HTML options
html_theme = 'saltstack'
html_theme_path = ['_themes']
html_title = None
html_short_title = project

html_static_path = ['_static']
html_logo = None # specfied in the theme layout.html
html_favicon = 'favicon.ico'
html_use_smartypants = False

html_default_sidebars = [
    'localtoc.html',
    'relations.html',
    'sourcelink.html',
    'searchbox.html',
]

html_context = {
    'html_default_sidebars': html_default_sidebars,
}


### Latex options
latex_logo = '_static/salt-logo.pdf'
latex_documents = [
    ('contents', 'Raet.tex', document_title, author, 'manual'),
]


### Manpage options
man_pages = [
    ('index', 'raet', document_title, [author], 1),
]


### epub options
epub_title = document_title
epub_author = author
epub_publisher = author
epub_copyright = copyright

epub_scheme = 'URL'
epub_identifier = 'http://raet.docs.saltstack.org/'


def _normalize_version(args):
    _, path = args
    return '.'.join([x.zfill(4) for x in (path.split('/')[-1].split('.'))])

class ReleasesTree(TocTree):
    option_spec = dict(TocTree.option_spec)

    def run(self):
        rst = super(ReleasesTree, self).run()
        entries = rst[0][0]['entries'][:]
        entries.sort(key=_normalize_version, reverse=True)
        rst[0][0]['entries'][:] = entries
        return rst


def setup(app):
    app.add_directive('releasestree', ReleasesTree)
