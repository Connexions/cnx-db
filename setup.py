# -*- coding: utf-8 -*-
import os
import sys

import versioneer
from setuptools import setup, find_packages


here = os.path.abspath(os.path.dirname(__file__))


def _filter_requirement(req):
    req = req.strip()
    # skip comments and dash options (e.g. `-e` & `-r`)
    return bool(req and req[0] not in '#-')


def read_from_requirements_txt(filepath):
    f = os.path.join(here, filepath)
    with open(f) as fb:
        return tuple([
            x.strip()
            for x in fb
            if _filter_requirement(x)
        ])


install_requires = read_from_requirements_txt('requirements/main.txt')
tests_require = read_from_requirements_txt('requirements/test.txt')
extras_require = {
    'test': tests_require,
}
description = "Connexions Database Library"
with open('README.rst', 'r') as readme, \
     open('docs/changes.rst', 'r') as changes:
    long_description = '\n'.join([
        readme.read(),
        changes.read(),
    ])


setup(
    name='cnx-db',
    version=versioneer.get_version(),
    author='Connexions team',
    author_email='info@cnx.org',
    url="https://github.com/connexions/cnx-db",
    license='LGPL, See also LICENSE.txt',
    description=description,
    long_description=long_description,
    install_requires=install_requires,
    tests_require=tests_require,
    extras_require=extras_require,
    packages=find_packages(exclude=['tests', 'tests.*']),
    include_package_data=True,
    package_data={
        'cnxdb': ['*-sql/*.sql', '*-sql/**/*.sql', 'schema/*.json'],
        },
    cmdclass=versioneer.get_cmdclass(),
    entry_points="""\
    [console_scripts]
    cnx-db = cnxdb.cli.main:main
    [dbmigrator]
    migrations_directory = cnxdb:migrations
    [pytest11]
    cnx-db = cnxdb.contrib.pytest
    """,
    )
