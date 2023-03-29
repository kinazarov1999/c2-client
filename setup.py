from setuptools import setup, find_packages

import os
import sys

from c2client import __version__

PACKAGE_PATH = os.path.abspath(os.path.dirname(__file__))

def get_description():
    with open(os.path.join(PACKAGE_PATH, "README.rst")) as readme:
        return readme.read()

install_requires = [
    "boto",
    "boto3",
    "inflection==0.3.1",
    "lxml",
    "six",
]
# argparse moved to stdlib in python2.7
if sys.version_info[0] == 2 and sys.version_info[1] <= 6:
    install_requires.append("argparse")

console_scripts = [
    "c2-{0} = c2client.shell:{0}_main".format(name)
    for name in ("ct", "cw", "ec2", "eks", "as", "elb", "bs", "paas")
]
console_scripts.append("c2rc-convert = c2client.c2rc_convert:main")


setup(
    name="c2client",
    version=__version__,
    description="CROC Cloud Platform - API Client",
    long_description=get_description(),
    url="https://github.com/c2devel/c2-client",
    license="GPL3",
    author="CROC Cloud Team",
    author_email="devel@croc.ru",
    maintainer="Andrey Kulaev",
    maintainer_email="adkulaev@gmail.com",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Environment :: Console",
        "Intended Audience :: Developers",
        "Intended Audience :: System Administrators",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 2.6",
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3",
    ],
    install_requires=install_requires,
    packages=find_packages(),
    entry_points={
        "console_scripts": console_scripts,
    },
)
