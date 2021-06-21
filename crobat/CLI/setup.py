"""
the setup.py for making a command line interface out of csv_out_test_w_args.py
"""


from setuptools import setup
setup(
    name='crobat_cli',
    version='0.0.1',
    entry_points={
        'console_scripts': [
            'crobat_cli=crobat_cli:crobat_cli'
        ]
    }
)