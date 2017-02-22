# -*- coding: utf-8 -*-
"""This module coordinates the software components that make up the integration
framework.

"""
import logging

import networkx
import numpy as np
from smif.intervention import Intervention, InterventionRegister
from smif.decision import Planning
from smif.sector_model import SectorModelBuilder, SectorModelMode

__author__ = "Will Usher"
__copyright__ = "Will Usher"
__license__ = "mit"


class Controller:
    """Coordinates the data-layer, decision-layer and model-runner

    The Controller expects to be provided with configuration data to run a set
    of sector models over a number of timesteps, in a given mode.

    It also requires a data connection to populate model inputs and store
    results.

    Parameters
    ----------
    config_data : dict
        A valid system-of-systems model configuration dictionary


    """
    def __init__(self, config_data):
        builder = SosModelBuilder()
        builder.construct(config_data)
        self._model = builder.finish()

    def run_sos_model(self):
        """Runs the system-of-system model
        """
        self._model.run()

    def run_sector_model(self, model_name):
        """Runs a sector model

        Parameters
        ----------
        model_name: str
            The name of the sector model to run
        """
        self._model.run_sector_model(model_name)


class SosModel(object):
    """Consists of the collection of timesteps and sector models

    This is NISMOD - i.e. the system of system model which brings all of the
    sector models together. Sector models may be joined through dependencies.

    This class is populated at runtime by the :class:`SosModelBuilder` and
    called from the :class:`Controller`.

    Attributes
    ==========
    model_list : dict
        This is a dictionary of :class:`smif.SectorModel`

    """
    def __init__(self):
        self.model_list = {}
        self._timesteps = []
        self.initial_conditions = []
        self.interventions = InterventionRegister()
        self.planning = None

        self.logger = logging.getLogger(__name__)

    def run(self):
        """Runs the system-of-system model

        0. Determine run mode

        1. Determine running order

        2. Run each sector model

        3. Return success or failure

        Notes
        =====
        # TODO pass in:


        - decisions, anything from strategy space that can be decided by
          explicit planning or rule-based decisions or the optimiser

        - state, anything from the previous timestep (assets with all
          attributes, state/condition of any other model entities)

        - data, anything from scenario space, to be used by the
          simulation of the model

        driven by needs of optimise routines, possibly all these
        parameters should be np arrays, or return np arrays from helper
        or have _simulate_from_array method

        # TODO pick state from previous timestep (or initialise)

        # TODO decide on approach to infrastructure system and possible
        actions/decisions which can change it, then handle system
        initialisation and keeping track of system composition over
        each timestep of the model run

        """
        mode = self.determine_running_mode

        if mode == SectorModelMode.static_simulation:
            self._run_static_sos_model
        elif mode == SectorModelMode.sequential_simulation:
            self._run_sequential_sos_model
        elif mode == SectorModelMode.static_optimisation:
            self._run_static_optimisation
        elif mode == SectorModelMode.dynamic_optimisation:
            self._run_dynamic_optimisation

    def _run_static_sos_model(self):
        """Runs the system-of-system model for one timeperiod

        Calls each of the sector models in the order required by the graph of
        dependencies, passing in the year for which they need to run.

        """
        run_order = self._get_model_names_in_run_order()

        timestep = self._timesteps[0]
        for model_name in run_order:
            model = self.model_list[model_name]
            model.simulate(timestep)

    def _run_sequential_sos_model(self):
        """Runs the system-of-system model sequentially

        """
        run_order = self._get_model_names_in_run_order()
        for timestep in self.timesteps:
            for model_name in run_order:
                model = self.model_list[model_name]
                model.simulate(timestep)

    def _run_static_optimisation(self):
        """Runs the system-of-systems model in a static optimisation format
        """
        raise NotImplementedError

    def _run_dynamic_optimisation(self):
        """Runs the system-of-system models in a dynamic optimisation format
        """
        raise NotImplementedError

    def _get_model_names_in_run_order(self):
        # topological sort gives a single list from directed graph
        return networkx.topological_sort(self.dependency_graph)

    def determine_running_mode(self):
        """Determines from the config in what mode to run the model

        Returns
        =======
        :class:`SectorModelMode`
            The mode in which to run the model
        """

        number_of_timesteps = len(self._timesteps)

        if number_of_timesteps > 1:
            # Run a sequential simulation
            mode = SectorModelMode.sequential_simulation

        elif number_of_timesteps == 0:
            raise ValueError("No timesteps have been specified")

        else:
            # Run a single simulation
            mode = SectorModelMode.static_simulation

        return mode

    def run_sector_model(self, model_name):
        """Runs the sector model

        Parameters
        ----------
        model_name : str
            The name of the model, corresponding to the folder name in the
            models subfolder of the project folder
        """
        msg = "Model {} does not exist. Choose from {}".format(model_name,
                                                               self.model_list)
        assert model_name in self.model_list, msg

        msg = "Running the {} sector model".format(model_name)
        self.logger.info(msg)

        sector_model = self.model_list[model_name]
        # Run a simulation for a single year
        # TODO fix assumption of no decision vars
        decision_variables = np.zeros(2)
        state = {}
        data = {}
        sector_model.simulate(decision_variables, state, data)

    @property
    def timesteps(self):
        """Returns the list of timesteps

        Returns
        =======
        list
            A list of timesteps
        """
        return sorted(self._timesteps)

    @property
    def intervention_names(self):
        """Names (id-like keys) of all known asset type
        """
        return [intervention.name for intervention in self.interventions]

    @timesteps.setter
    def timesteps(self, value):
        self._timesteps = value

    @property
    def sector_models(self):
        """The list of sector model names

        Returns
        =======
        list
            A list of sector model names
        """
        return list(self.model_list.keys())

    def sequential_simulation(self, model, inputs, decisions):
        """Runs a sequence of simulations to cover each of the model timesteps
        """
        results = []
        for index in range(len(self.timesteps)):
            # Intialise the model
            model.inputs = inputs
            # Update the state from the previous year
            if index > 0:
                state_var = 'existing capacity'
                state_res = results[index - 1]['capacity']
                self.logger.debug("Updating %s with %s", state_var, state_res)
                model.inputs.parameters.update_value(state_var, state_res)

            # Run the simulation
            decision = decisions[index]
            state = {}
            data = {}
            results.append(model.simulate(decision, state, data))
        return results


class SosModelBuilder(object):
    """Constructs a system-of-systems model

    Builds a :class:`SosModel`.

    Examples
    --------
    Call :py:meth:`~controller.SosModelBuilder.construct` to populate
    a :class:`SosModel` object and :py:meth:`~controller.SosModelBuilder.finish`
    to return the validated and dependency-checked system-of-systems model.

    >>> builder = SosModelBuilder()
    >>> builder.construct(config_data)
    >>> builder.finish()

    """
    def __init__(self):
        self.sos_model = SosModel()

        self.logger = logging.getLogger(__name__)

    def construct(self, config_data):
        """Set up the whole SosModel

        Parameters
        ----------
        config_data : dict
            A valid system-of-systems model configuration dictionary
        """
        model_list = config_data['sector_model_data']

        self.add_timesteps(config_data['timesteps'])
        self.load_models(model_list)
        self.add_planning(config_data['planning'])

        models = self.sos_model.model_list.values()

    def add_timesteps(self, timesteps):
        """Set the timesteps of the system-of-systems model

        Parameters
        ----------
        timesteps : list
            A list of timesteps
        """
        self.sos_model.timesteps = timesteps

    def load_models(self, model_data_list):
        """Loads the sector models into the system-of-systems model

        Parameters
        ----------
        model_data_list : list
            A list of sector model config/data
        assets : list
            A list of assets to pass to the sector model

        """
        for model_data in model_data_list:
            model = self._build_model(model_data)
            self.add_model(model)

    @staticmethod
    def _build_model(model_data):
        builder = SectorModelBuilder(model_data['name'])
        builder.load_model(model_data['path'], model_data['classname'])
        builder.add_inputs(model_data['inputs'])
        builder.add_outputs(model_data['outputs'])
        builder.add_interventions(model_data['interventions'])
        return builder.finish()

    def add_model(self, model):
        """Adds a sector model to the system-of-systems model

        Parameters
        ----------
        model : :class:`smif.sector_model.SectorModel`
            A sector model wrapper

        """
        self.logger.info("Loading model: %s", model.name)
        self.sos_model.model_list[model.name] = model

        for intervention in model.interventions:
            intervention_object = Intervention(sector=model.name,
                                               data=intervention)
            msg = "Adding {} from {} to SOSModel InterventionRegister"
            identifier = intervention_object.name
            self.logger.debug(msg.format(identifier, model.name))
            self.sos_model.interventions.register(intervention_object)

    def add_planning(self, planning):
        """Loads the planning logic into the system of systems model

        Pre-specified planning interventions are defined at the sector-model
        level, read in through the SectorModel class, but populate the
        intervention register in the controller.

        Parameters
        ----------
        planning : list
            A list of planning instructions

        """
        self.sos_model.planning = Planning(planning)

    def _check_planning_assets_exist(self):
        """Check existence of all the assets in the pre-specifed planning

        """
        model = self.sos_model
        names = model.intervention_names
        for planning_name in model.planning.names:
            msg = "Asset '{}' in planning file not found in assets"
            assert planning_name in names, msg.format(planning_name)

    def _check_planning_timeperiods_exist(self):
        """Check existence of all the timeperiods in the pre-specified planning
        """
        model = self.sos_model
        model_timeperiods = model.timesteps
        for timeperiod in model.planning.timeperiods:
            msg = "Timeperiod '{}' in planning file not found model config"
            assert timeperiod in model_timeperiods, msg.format(timeperiod)

    def _validate(self):
        """Validates the sos model
        """
        self._check_planning_assets_exist()
        self._check_planning_timeperiods_exist()

    def _check_dependencies(self):
        """For each model, compare dependency list of from_models
        against list of available models
        """
        dependency_graph = networkx.DiGraph()
        models_available = self.sos_model.sector_models
        dependency_graph.add_nodes_from(models_available)

        for model_name, model in self.sos_model.model_list.items():
            for dep in model.inputs.dependencies:
                if dep.from_model not in models_available and dep.from_model != "scenario":
                    # report missing dependency type
                    msg = "Missing dependency: {} depends on {} from {}, " + \
                          "which is not supplied."
                    raise AssertionError(msg.format(model_name, dep.name, dep.from_model))
                dependency_graph.add_edge(model_name, dep.from_model)

        if not networkx.is_directed_acyclic_graph(dependency_graph):
            raise NotImplementedError("Graph of dependencies contains a cycle.")

        self.sos_model.dependency_graph = dependency_graph

    def finish(self):
        """Returns a configured system-of-systems model ready for operation

        - includes validation steps, e.g. to check dependencies
        """
        self._validate()
        self._check_dependencies()
        return self.sos_model
