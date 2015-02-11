"""
setup.py

Basic setup file to enable pip install
See:
    http://pythonhosted.org//setuptools/setuptools.html
    https://pypi.python.org/pypi/setuptools

python setup.py register sdist upload

"""
import os
import  sys
from setuptools import setup, find_packages

# Change to RAET's source's directory prior to running any command
try:
    SETUP_DIRNAME = os.path.dirname(__file__)
except NameError:
    # We're most likely being frozen and __file__ triggered this NameError
    # Let's work around that
    SETUP_DIRNAME = os.path.dirname(sys.argv[0])

if SETUP_DIRNAME != '':
    os.chdir(SETUP_DIRNAME)

SETUP_DIRNAME = os.path.abspath(SETUP_DIRNAME)

RAET_METADATA = os.path.join(SETUP_DIRNAME, 'raet', '__metadata__.py')

# Load the metadata using exec() in order not to trigger raet.__init__ import
exec(compile(open(RAET_METADATA).read(), RAET_METADATA, 'exec'))

REQUIREMENTS = ['ioflo>=1.1.7',
                'libnacl>=1.4.0',
                'six>=1.6.1', ]

if sys.version_info < (2, 7): #tuple comparison element by element
    # Under Python 2.6, also install
    REQUIREMENTS.extend([
        'importlib>=1.0.3',
        'argparse>=1.2.1'
    ])

if sys.version_info < (3, 4): #tuple comparison element by element
    REQUIREMENTS.extend([
        'enum34>=1.0.4',
    ])

setup(
    name='raet',
    version=__version__,
    description='Reliable Asynchronous Event Transport protocol',
    long_description='Asynchronous transaction based protocol'
                     ' using Ioflo. http://ioflo.com',
    url='https://github.com/saltstack/raet',
    download_url='https://github.com/saltstack/raet/archive/master.zip',
    author=__author__,
    author_email='info@ioflo.com',
    license=__license__,
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
    install_requires=REQUIREMENTS,
    extras_require={},
    scripts=['scripts/raetflo'],)

