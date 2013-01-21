import os
import sys

from setuptools import find_packages
from setuptools import setup



PY3K = sys.version_info >= (3,0)
readme = open(os.path.join(os.path.dirname(__file__), 'README.rst')).read()

setup(
    name='pyramid_webforms',
    version='0.0.1',
    packages=find_packages(exclude=['tests']),
    install_requires=[
        'FormEncode>=1.2.6',
        'pyramid>=1.4',
        'webhelpers>=1.3',
        'six',
        'Babel',
        'lingua',
    ],
    message_extractors={'.': [
        ('**.py', 'lingua_python', None),
    ]},
    setup_requires=['nose>=1.1.2'],
    tests_require=['coverage'],
    package_data={
        # If any package contains listed files, include them
        '':['*.txt', '*.rst', '*mako', '*.mo']
    },
    include_package_data=True,

    # PyPI metadata
    # Read more on http://docs.python.org/distutils/setupscript.html#meta-data
    author="Maxim Avanov",
    author_email="maxim.avanov@gmail.com",
    maintainer="Maxim Avanov",
    maintainer_email="maxim.avanov@gmail.com",
    description="Simple declarative web forms using FormEncode and WebHelpers",
    long_description=readme,
    license="MIT",
    url="https://github.com/2nd/pyramid_webforms",
    download_url="https://github.com/2nd/pyramid_webforms",
    keywords="pyramid formencode forms templates validation",
    # See the full list on http://pypi.python.org/pypi?%3Aaction=list_classifiers
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Environment :: Web Environment',
        'Framework :: Pyramid',
        'Intended Audience :: Developers',
        'License :: OSI Approved',
        'License :: OSI Approved :: MIT License',
        'Operating System :: MacOS',
        'Operating System :: Microsoft',
        'Operating System :: POSIX',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2.7',
        'Topic :: Internet :: WWW/HTTP',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
        'Topic :: Software Development :: Libraries :: Python Modules',
        ]
)
