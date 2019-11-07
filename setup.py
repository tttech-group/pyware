import datetime
import sys
import os
from setuptools import setup

YEAR = datetime.date.today().year

# With older Python, we must specify all package level
if sys.version_info <= (3, 3):
    packages = ['tttech']
else:
    packages = []

# The real package in the folder ./tttech/dbdict
packages.append('tttech.pyware')

dist_files = ['RELEASE_NOTES.txt', 'README.md']

# Settings for the package
setup(
    name='pyware',
    version_prefix="pyware",
    description='Python-client for WADL-based REST-API',
    license='Copyright (C) %s TTTech Computertechnik AG. All rights reserved' % YEAR,
    author='Duc-Hung Le',
    author_email='duc-hung.le@opensource.tttech.com',
    url='https://github.com/tttech-group',
    classifiers=[
        "License :: GNU LESSER GENERAL PUBLIC LICENSE (LGPL)",  #
        "Programming Language :: Python :: %d.%d" % (sys.version_info.major, sys.version_info.minor),
        "Operating System :: POSIX :: Linux",
    ],
    packages=packages,
    entry_points={
        'console_scripts': [
            'pyware = tttech.pyware.docs_handler:main'
        ],
    },
    install_requires=[
        'requests',
        'requests_kerberos',
        'lxml',
    ],
    include_package_data=True,
    dist_files=dist_files)
