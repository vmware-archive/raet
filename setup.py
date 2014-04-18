"""
setup.py

Basic setup file to enable pip install
See:
    http://pythonhosted.org//setuptools/setuptools.html
    https://pypi.python.org/pypi/setuptools

python setup.py register sdist upload

"""
import  sys
from setuptools import setup, find_packages

import raet

PYTHON26_REQUIRES = []
if sys.version_info < (2, 7): #tuple comparison element by element
    PYTHON26_REQUIRES.append('importlib>=1.0.3')
    PYTHON26_REQUIRES.append('argparse>=1.2.1')

setup(
    name='raet',
    version=raet.__version__,
    description='Reliable Asynchronous Event Transport protocol',
    long_description='Asynchronous transaction based protocol'
                     ' using Ioflo. http://ioflo.com',
    url='https://github.com/saltstack/raet',
    download_url='https://github.com/saltstack/raet/archive/master.zip',
    author=raet.__author__,
    author_email='info@ioflo.com',
    license=raet.__license__,
    keywords=('UDP UXD Communications CurveCP Elliptic Curve Crypto'
              'Reliable Asynchronous Event Transport Protocol'),
    packages=find_packages(exclude=['test', 'test.*',
                                      'docs', 'docs*',
                                      'log', 'log*']),
    package_data={
        '':       ['*.txt',  '*.md', '*.rst', '*.json', '*.conf', '*.html',
                   '*.css', '*.ico', '*.png', 'LICENSE', 'LEGAL'],
        'raet': ['flo/plan/*.flo', 'flo/plan/*/*.flo',
                  'flo/plan/*.txt', 'flo/plan/*/*.txt',],},
    install_requires=([] + PYTHON26_REQUIRES),
    extras_require={},
    scripts=['scripts/raetflo'],)

