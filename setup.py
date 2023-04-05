from setuptools import setup, find_packages

import os

from c2client import entrypoints, __version__


PACKAGE_PATH = os.path.abspath(os.path.dirname(__file__))


def get_description():
    with open(os.path.join(PACKAGE_PATH, "README.rst")) as readme:
        return readme.read()


install_requires = [
    "boto",
    "boto3",
    "inflection==0.3.1",
    "lxml",
]


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
        "Programming Language :: Python :: 3",
    ],
    install_requires=install_requires,
    packages=find_packages(),
    entry_points={
        "console_scripts": [
            f"{name} = c2client.shell:{client}.execute"
            for name, client in entrypoints
        ]
    },
)
