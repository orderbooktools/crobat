"""
setup.py

Install the crobat package:
    pip install -e .      (editable, from the crobat/ project root)
    pip install .         (standard install)

After installation the crobat package is importable from anywhere and
the `crobat` CLI command is available system-wide.
"""

from setuptools import setup, find_packages

setup(
    name="crobat",
    version="1.0.0",
    description="Cryptocurrency Order Book Analysis Tool",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    author="Ivan E. Perez",
    author_email="perez.ivan.e@gmail.com",
    url="https://github.com/orderbooktools/crobat",
    license="GPLv3",
    packages=find_packages(exclude=["tests*"]),
    install_requires=[
        "coinbase-advanced-py==1.8.2",
        "numpy",
        "pandas",
    ],
    entry_points={
        "console_scripts": [
            "crobat=CLI.crobat_cli:main",
        ],
    },
    python_requires=">=3.10",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        "Operating System :: OS Independent",
        "Topic :: Office/Business :: Financial",
        "Topic :: Scientific/Engineering :: Information Analysis",
    ],
)
