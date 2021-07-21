#mysupercoolscript.py
    
import os
import click
import sys
import os
    
@click.group()
@click.pass_context
def crobat_cli(self):
    pass
  
@crobat_cli.command()
def collect_data():
    """????? yet"""
    print("Starting to collect data")
    os.chdir = ()
    from .tests import CSV_out_test_w_args
    CSV_out_test_w_args.main()

cli = click.CommandCollection(sources=[crobat_cli])
 
if __name__ == '__main__':
    crobat_cli()