# -*- coding: utf-8 -*-
"""A command line interface to the system of systems framework

This command line interface implements a number of methods.

- `setup` creates an example project with the recommended folder structure
- `run` performs a simulation of an individual sector model, or the whole system
        of systems model
- `validate` performs a validation check of the configuration file
- `app` runs the graphical user interface, opening in a web browser

Folder structure
----------------

When configuring a project for the CLI, the folder structure below should be
used.  In this example, there is one system-of-systems model, combining a water
supply and an energy demand model::

    /config
        project.yaml
        /sector_models
            energy_demand.yml
            water_supply.yml
        /sos_models
            energy_water.yml
        /model_runs
            run_to_2050.yml
            short_test_run.yml
            ...
    /data
        /initial_conditions
            reservoirs.yml
        /interval_definitions
            annual_intervals.csv
        /interventions
            water_supply.yml
        /narratives
            high_tech_dsm.yml
        /region_definitions
            /oxfordshire
                regions.geojson
            /uk_nations_shp
                regions.shp
        /scenarios
            population.csv
            raininess.csv
        /water_supply
            /initial_system
    /models
        energy_demand.py
        water_supply.py
    /planning
        expected_to_2020.yaml
        national_infrastructure_pipeline.yml

The sector model implementations can be installed independently of the model run
configuration. The paths to python wrapper classes (implementing SectorModel)
should be specified in each ``sector_model/*.yml`` configuration.

The project.yaml file specifies the metadata shared by all elements of the
project; ``sos_models`` specify the combinations of ``sector_models`` and
``scenarios`` while individual ``model_runs`` specify the scenario, strategy
and narrative combinations to be used in each run of the models.

"""
from __future__ import print_function

import logging
import os
import sys
import warnings
from argparse import ArgumentParser

import pkg_resources

import smif
import smif.cli.log
from smif.controller import (ModelRunScheduler, copy_project_folder,
                             execute_model_run)
from smif.data_layer import Store
from smif.data_layer.file import (CSVDataStore, FileMetadataStore,
                                  ParquetDataStore, YamlConfigStore)
from smif.http_api import create_app

try:
    import _thread
except ImportError:
    import thread as _thread

try:
    import win32api

    USE_WIN32 = True
except ImportError:
    USE_WIN32 = False

__author__ = "Will Usher, Tom Russell"
__copyright__ = "Will Usher, Tom Russell"
__license__ = "mit"


def list_model_runs(args):
    """List the model runs defined in the config, optionally indicating whether complete
    results exist.
    """
    store = _get_store(args)
    model_run_configs = store.read_model_runs()

    if args.complete:
        print('Model runs with an asterisk (*) have complete results available\n')

    for run in model_run_configs:
        run_name = run['name']

        if args.complete:
            expected_results = store.canonical_expected_results(run_name)
            available_results = store.canonical_available_results(run_name)

            complete = ' *' if expected_results == available_results else ''

            print('{}{}'.format(run_name, complete))
        else:
            print(run_name)


def list_available_results(args):
    """List the available results for a specified model run.
    """

    store = _get_store(args)
    expected = store.canonical_expected_results(args.model_run)
    available = store.available_results(args.model_run)

    # Print run and sos model
    run = store.read_model_run(args.model_run)
    print('\nmodel run: {}'.format(args.model_run))
    print('{}- sos model: {}'.format(' ' * 2, run['sos_model']))

    # List of expected sector models
    sec_models = sorted({sec for _t, _d, sec, _out in expected})

    for sec_model in sec_models:
        print('{}- sector model: {}'.format(' ' * 4, sec_model))

        # List expected outputs for this sector model
        outputs = sorted({out for _t, _d, sec, out in expected if sec == sec_model})

        for output in outputs:
            print('{}- output: {}'.format(' ' * 6, output))

            # List available decisions for this sector model and output
            decs = sorted({d for _t, d, sec, out in available if
                           sec == sec_model and out == output})

            if len(decs) == 0:
                print('{}- no results'.format(' ' * 8))

            for dec in decs:
                base_str = '{}- decision {}:'.format(' ' * 8, dec)

                # List available time steps for this decision, sector model and output
                ts = sorted({t for t, d, sec, out in available if
                             d == dec and sec == sec_model and out == output})
                assert (len(
                    ts) > 0), "If a decision is available, so is at least one time step"

                res_str = ', '.join([str(t) for t in ts])
                print('{} {}'.format(base_str, res_str))


def list_missing_results(args):
    """List the missing results for a specified model run.
    """

    store = _get_store(args)
    expected = store.canonical_expected_results(args.model_run)
    missing = store.canonical_missing_results(args.model_run)

    # Print run and sos model
    run = store.read_model_run(args.model_run)
    print('\nmodel run: {}'.format(args.model_run))
    print('{}- sos model: {}'.format(' ' * 2, run['sos_model']))

    # List of expected sector models
    sec_models = sorted({sec for _t, _d, sec, _out in expected})

    for sec_model in sec_models:
        print('{}- sector model: {}'.format(' ' * 4, sec_model))

        # List expected outputs for this sector model
        outputs = sorted({out for _t, _d, sec, out in expected if sec == sec_model})

        for output in outputs:
            print('{}- output: {}'.format(' ' * 6, output))

            # List missing time steps for this sector model and output
            ts = sorted({t for t, d, sec, out in missing if
                         sec == sec_model and out == output})

            if len(ts) == 0:
                print('{}- no missing results'.format(' ' * 8))
            else:
                base_str = '{}- results missing for:'.format(' ' * 8)
                res_str = ', '.join([str(t) for t in ts])
                print('{} {}'.format(base_str, res_str))

def prepare_scenario(args):
    """ Create {scenario_name}.yml from {scenario_name}_template.yml 
        scenario file to include multiple scenario variants.
    """
    config_store = _get_store(args).config_store
    list_of_variants = range(args.variants_range[0], args.variants_range[1]+1)

    # path to scenario file
    full_path = os.path.join(config_store.config_folders['scenarios'],
                             args.scenario_name+'.yml')
    full_path_template = os.path.join(config_store.config_folders['scenarios'],
                                      args.scenario_name+'_template.yml')

    # check that template file exists
    if not os.path.isfile(full_path_template):
        raise FileNotFoundError('Could not found template file {}.'.format(full_path_template))
    # check if scenario file already exists and ask permission from user for overwriting it
    if os.path.isfile(full_path):
        print("File {} has been found and will be overwritten."
              "Continue ? [y/n]".format(full_path))
        yes_or_no = input()
        while(True):
            if yes_or_no=='yes' or yes_or_no=='y':
                break
            elif yes_or_no=='no' or yes_or_no=='n':
                sys.exit('Abort.')
            else:
                print('Please answer yes or no [y/n]')
        
    """Copy the template {args.scenario_name}_template.yml to {args.scenario_name}.yml the
       config/scenarios/ directory
    """
    copy_template_file = 'cp '+full_path_template+' '+full_path
    os.system(copy_template_file)

    scenario = config_store.read_scenario(args.scenario_name)
    # check that template scenario file does not have more than one variant
    if len(scenario['variants'])<1:
        sys.exit('Template file {} must define a template variant'.format(full_path_template))
    elif len(scenario['variants'])>1:
        warnings.warn("More than one variant found in scenario "
                      "template file {}.".format(full_path_template))
    variant_template_name = scenario['variants'][0]['name']
    # Get first variant defined in template scenario file
    variant = config_store.read_scenario_variant(args.scenario_name, variant_template_name)

    root = {}
    """ root is a dict. keyed on scenario outputs. 
        Entries contain the root of the variants filenames
    """
    for output in scenario['provides']:
        root[output['name']], ext = os.path.splitext(variant['data'][output['name']])

    # Now modify scenario file
    first_variant = True
    for ivar in list_of_variants:
        for output in scenario['provides']:
            variant['name'] = args.scenario_name+'_{:d}'.format(ivar)
            variant['data'][output['name']] = root[output['name']]+'{:d}'.format(ivar)+ext
        if(first_variant):
            first_variant = False
            config_store.update_scenario_variant(args.scenario_name,
                                                    variant_template_name, variant)
        else:
            config_store.write_scenario_variant(args.scenario_name, variant)

def prepare_model_run(args):
    config_store = _get_store(args).config_store
    mr_name = args.model_run_name
    sc_name = args.scenario_name

    model_run = config_store.read_model_run(mr_name)
    if not(sc_name in model_run['scenarios']):
        raise FileNotFOundError('Error: Unknown scenario')
    path_to_scenario=os.path.join(config_store.config_folders['scenarios'],
                                  sc_name+'.yml')
    if not(os.path.isfile(path_to_scenario)):
           raise FileNotFoundError("Error: Could not find "
                                   "scenario file {}".format(path_to_scenario))
    
    # Read scenario
    scenario=config_store.read_scenario(sc_name)
    # Define default lower and upper of variant range
    var_start = 0
    var_end = len(scenario['variants'])

    # Check if optional cli arguments specify range of variants
    # They are compared to None because they can be 0
    if args.start!=None:
        var_start = args.start;
        if var_start<0:
            raise ValueError('Lower bound of variant range must be >=0')
        if var_start>len(scenario['variants']):
            raise ValueError("Lower bound of variant range greater"
                             " than number of variants")
    if args.end!=None:
        var_end = args.end
        if var_end<0:
            raise ValueError('Upper bound of variant range must be >=0')
        if var_end>len(scenario['variants'])-1:
            raise ValueError("Upper bound of variant range cannot be greater"
                             " than {:d}".format(len(scenario['variants'])-1))
        if var_end<var_start:
            raise ValueError("Upper bound of variant range must be >= lower" 
                             " bound of variant range")

    # Open batchfile
    f_handle = open(mr_name+'.batch', 'w')
    # For each variant model_run, write a new model run file with corresponding
    # scenario variant and update batchfile.
    for variant in scenario['variants'][var_start:var_end+1]:
        variant_model_run_name = mr_name+'_'+variant['name']
        model_run['name'] = variant_model_run_name
        model_run['scenarios'][sc_name] = variant['name']

        # Check if model run definition already exist and erase if permission
        # to overwrite. Needed because YamlConfigStore.write_model_run() throws an error
        # of model run file already exists.
        full_path = os.path.join(config_store.config_folders['model_runs'],
                                 model_run['name']+'.yml')
        if os.path.isfile(full_path):
            print("File {} has been found and will be overwritten."
                  "Continue ? [y/n]".format(full_path))
            yes_or_no = input()
            while(True):
                if yes_or_no=='yes' or yes_or_no=='y':
                    os.system('rm '+full_path)     
                    break
                elif yes_or_no=='no' or yes_or_no=='n':
                    sys.exit('Abort.')
                else:
                    print('Please answer yes or no [y/n]')
        # Write model run file and update batchfile.        
        config_store.write_model_run(model_run)
        f_handle.write(mr_name+'_'+variant['name']+'\n')
        
    # Close batchfile
    f_handle.close()

def run_model_runs(args):
    """Run the model runs as requested. Check if results exist and asks
    user for permission to overwrite

    Parameters
    ----------
    args
    """
    logger = logging.getLogger(__name__)
    logger.profiling_start('run_model_runs', '{:s}, {:s}, {:s}'.format(
        args.modelrun, args.interface, args.directory))
    if args.batchfile:
        with open(args.modelrun, 'r') as f:
            model_run_ids = f.read().splitlines()
    else:
        model_run_ids = [args.modelrun]

    store = _get_store(args)
    execute_model_run(model_run_ids, store, args.warm)
    logger.profiling_stop('run_model_runs', '{:s}, {:s}, {:s}'.format(
        args.modelrun, args.interface, args.directory))
    logger.summary()


def _get_store(args):
    """Contruct store as configured by arguments
    """
    if args.interface == 'local_csv':
        store = Store(
            config_store=YamlConfigStore(args.directory),
            metadata_store=FileMetadataStore(args.directory),
            data_store=CSVDataStore(args.directory),
            model_base_folder=args.directory
        )
    elif args.interface == 'local_binary':
        store = Store(
            config_store=YamlConfigStore(args.directory),
            metadata_store=FileMetadataStore(args.directory),
            data_store=ParquetDataStore(args.directory),
            model_base_folder=args.directory
        )
    else:
        raise ValueError("Store interface type {} not recognised.".format(args.interface))
    return store


def _run_server(args):
    app_folder = pkg_resources.resource_filename('smif', 'app/dist')
    app = create_app(
        static_folder=app_folder,
        template_folder=app_folder,
        data_interface=_get_store(args),
        scheduler=ModelRunScheduler()
    )
    port = 5000

    print("    Opening smif app\n")
    print("    Copy/paste this URL into your web browser to connect:")
    print("        http://localhost:" + str(port) + "\n")
    # add flush to ensure that text is printed before server thread starts
    print("    Close your browser then type Control-C here to quit.", flush=True)
    app.run(host='0.0.0.0', port=port, threaded=True)


def run_app(args):
    """Run the client/server application

    Parameters
    ----------
    args
    """
    # avoid one of two error messages from 'forrtl error(200)' when running
    # on windows cmd - seems related to scipy's underlying Fortran
    os.environ['FOR_DISABLE_CONSOLE_CTRL_HANDLER'] = 'T'

    if USE_WIN32:
        # Set handler for CTRL-C. Necessary to avoid `forrtl: error (200):
        # program aborting...` crash on CTRL-C if we're runnging from Windows
        # cmd.exe
        def handler(dw_ctrl_type, hook_sigint=_thread.interrupt_main):
            """Handler for CTRL-C interrupt
            """
            if dw_ctrl_type == 0:  # CTRL-C
                hook_sigint()
                return 1  # don't chain to the next handler
            return 0  # chain to the next handler
        win32api.SetConsoleCtrlHandler(handler, 1)

    # Create backend server process
    _run_server(args)


def setup_project_folder(args):
    """Setup a sample project
    """
    copy_project_folder(args.directory)


def parse_arguments():
    """Parse command line arguments

    Returns
    =======
    :class:`argparse.ArgumentParser`

    """
    parser = ArgumentParser(description='Command line tools for smif')
    parser.add_argument('-V', '--version',
                        action='version',
                        version="smif " + smif.__version__,
                        help='show the current version of smif')

    parent_parser = ArgumentParser(add_help=False)
    parent_parser.add_argument('-v', '--verbose',
                               action='count',
                               help='show messages: -v to see messages reporting on ' +
                               'progress, -vv to see debug messages.')
    parent_parser.add_argument('-i', '--interface',
                               default='local_csv',
                               choices=['local_csv', 'local_binary'],
                               help="Select the data interface (default: %(default)s)")
    parent_parser.add_argument('-d', '--directory',
                               default='.',
                               help="Path to the project directory")

    subparsers = parser.add_subparsers(help='available commands')

    # SETUP
    parser_setup = subparsers.add_parser(
        'setup', help='Setup the project folder', parents=[parent_parser])
    parser_setup.set_defaults(func=setup_project_folder)

    # LIST
    parser_list = subparsers.add_parser(
        'list', help='List available model runs', parents=[parent_parser])
    parser_list.set_defaults(func=list_model_runs)
    parser_list.add_argument('-c', '--complete',
                             help="Show which model runs have complete results",
                             action='store_true')

    # RESULTS
    parser_available_results = subparsers.add_parser(
        'available_results', help='List available results', parents=[parent_parser])
    parser_available_results.set_defaults(func=list_available_results)
    parser_available_results.add_argument(
        'model_run',
        help="Name of the model run to list available results"
    )

    parser_missing_results = subparsers.add_parser(
        'missing_results', help='List missing results', parents=[parent_parser])
    parser_missing_results.set_defaults(func=list_missing_results)
    parser_missing_results.add_argument(
        'model_run',
        help="Name of the model run to list missing results"
    )

    # PREPARE
    parser_prepare_scenario = subparsers.add_parser(
        'prepare-scenario', help='Prepare scenario configuration file with multiple variants',
        parents=[parent_parser])
    parser_prepare_scenario.set_defaults(func=prepare_scenario)
    parser_prepare_scenario.add_argument(
        'scenario_name', help='Name of the scenario')
    parser_prepare_scenario.add_argument(
        'variants_range', nargs=2, type=int,
        help='Two integers delimiting the range of variants')
        # PREPARE
    parser_prepare_model_run = subparsers.add_parser(
        'prepare-run', help='Prepare model runs based on scenario variants',
        parents=[parent_parser])
    parser_prepare_model_run.set_defaults(func=prepare_model_run)
    parser_prepare_model_run.add_argument(
        'scenario_name', help='Name of the scenario')
    parser_prepare_model_run.add_argument(
        'model_run_name', help='Name of the template model run')
    parser_prepare_model_run.add_argument(
        '-s', '--start', type=int, help='Lower bound of the range of variants')
    parser_prepare_model_run.add_argument(
        '-e', '--end', type=int, help='Upper bound of the range of variants')

    # APP
    parser_app = subparsers.add_parser(
        'app', help='Open smif app', parents=[parent_parser])
    parser_app.set_defaults(func=run_app)

    # RUN
    parser_run = subparsers.add_parser(
        'run', help='Run a model', parents=[parent_parser])
    parser_run.set_defaults(func=run_model_runs)
    parser_run.add_argument('-w', '--warm',
                            action='store_true',
                            help="Use intermediate results from the last modelrun \
                                  and continue from where it had left")
    parser_run.add_argument('-b', '--batchfile',
                            action='store_true',
                            help="Use a batchfile instead of a modelrun name (a \
                                  list of modelrun names)")
    parser_run.add_argument('modelrun',
                            help="Name of the model run to run")

    return parser


def confirm(prompt=None, response=False):
    """Prompts for a yes or no response from the user

    Arguments
    ---------
    prompt : str, default=None
    response : bool, default=False

    Returns
    -------
    bool
        True for yes and False for no.

    Notes
    -----

    `response` should be set to the default value assumed by the caller when
    user simply types ENTER.

    Examples
    --------

    >>> confirm(prompt='Create Directory?', response=True)
    Create Directory? [y]|n:
    True
    >>> confirm(prompt='Create Directory?', response=False)
    Create Directory? [n]|y:
    False
    >>> confirm(prompt='Create Directory?', response=False)
    Create Directory? [n]|y: y
    True

    """

    if prompt is None:
        prompt = 'Confirm'

    if response:
        prompt = '{} [{}]|{}: '.format(prompt, 'y', 'n')
    else:
        prompt = '{} [{}]|{}: '.format(prompt, 'n', 'y')

    while True:
        ans = input(prompt)
        if not ans:
            return response
        if ans not in ['y', 'Y', 'n', 'N']:
            print('please enter y or n.')
            continue
        if ans in ['y', 'Y']:
            return True
        if ans in ['n', 'N']:
            return False


def main(arguments=None):
    """Parse args and run
    """
    parser = parse_arguments()
    args = parser.parse_args(arguments)
    smif.cli.log.setup_logging(args.verbose)

    def exception_handler(exception_type, exception, traceback, debug_hook=sys.excepthook):
        if args.verbose:
            debug_hook(exception_type, exception, traceback)
        else:
            print("{}: {}".format(exception_type.__name__, exception))

    sys.excepthook = exception_handler

    if 'func' in args:
        args.func(args)
    else:
        parser.print_help()
