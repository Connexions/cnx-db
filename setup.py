# -*- coding: utf-8 -*-
import sys
from setuptools import setup, find_packages


IS_PY3 = sys.version_info > (3,)

setup_requires = (
    'pytest-runner',
    )
install_requires = (
    'psycopg2',
    'venusian',
    )
tests_require = [
    'pytest',
    ]
extras_require = {
    'test': tests_require,
    }
description = "Connexions Database Library"
with open('README.rst', 'r') as readme, \
     open('docs/changes.rst', 'r') as changes:
    long_description = '\n'.join([
        readme.read(),
        "==========\nChange Log\n==========",
        changes.read(),
    ])

if not IS_PY3:
    tests_require.append('mock==1.0.1')

setup(
    name='cnx-db',
    version='0.2.0',
    author='Connexions team',
    author_email='info@cnx.org',
    url="https://github.com/connexions/cnx-db",
    license='LGPL, See also LICENSE.txt',
    description=description,
    long_description=long_description,
    setup_requires=setup_requires,
    install_requires=install_requires,
    tests_require=tests_require,
    extras_require=extras_require,
    test_suite='cnxdb.tests',
    packages=find_packages(),
    include_package_data=True,
    package_data={
        'cnxdb': ['*-sql/*.sql', '*-sql/**/*.sql', 'schema/*.json'],
        'cnxdb.tests': ['data/init/**/*.*'],
        },
    entry_points="""\
    [console_scripts]
    cnx-db = cnxdb.cli.main:main
    """,
    )
