#mysupercoolscript.py
    
import os
import click
import sys
import os
os.chdir('..')
os.chdir('..')  
sys.path.append(os.getcwd())
print(sys.path)
#print(os.getcwd())

#print(os.getcwd())
#os.chdir('tests')
#print(os.getcwd())
import tests.CSV_out_test_w_input #.CSV_out_test_w_args 
import tests.CSV_out_test_w_args
@click.group()
@click.pass_context
def crobat_cli(self):
    pass
  
@crobat_cli.command()
def interface():
    """
    Initializes the sequence where one can enter arguments
    as inputs. 
    
    The session inputs required are:
        pair : str
        currency pair you would like to record.

        recording_duration : int
        recording duration in seconds

        position range : int
        ordinal depth you would like to record for

        sides : str
        sides in the output files
        example: bid,ask,signed

        filetypes: str
        output filetypes
        example: xlsx,csv,pkl
    """
    print("Starting CLI tool with args")
    tests.CSV_out_test_w_args.main()
    print("Starting inputs request cli wizard")
    tests.CSV_out_test_w_input.main()

# @crobat_cli.command()
# def using_args():
#     """
#     Initializes cli tool directly taking arguments for each parameter.

#     The parametersrequired are:
#         -pair : str
#         currency pair you would like to record.

#         -recording_duration : int
#         recording duration in seconds

#         -position_range : int
#         ordinal depth you would like to record for

#         -sides : str
#         sides in the output files
#         example: bid,ask,signed

#         -filetypes: str
#         output filetypes
#         example: xlsx,csv,pkl
#     """


cli = click.CommandCollection(sources=[crobat_cli])
 
if __name__ == '__main__':
    crobat_cli()