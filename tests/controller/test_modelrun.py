from copy import copy
from unittest.mock import Mock

from pytest import fixture, raises
from smif.controller.modelrun import (ModelRunBuilder, ModelRunError,
                                      ModelRunner)


@fixture(scope='function')
def config_data():
    """Config for a model run
    """
    sos_model = Mock()
    sos_model.name = "test_sos_model"
    sos_model.parameters = {}

    climate_scenario = Mock()
    climate_scenario.name = 'climate'
    sos_model.scenario_models = {'climate': climate_scenario}

    energy_supply = Mock()
    energy_supply.name = 'energy_supply'
    sos_model.models = [energy_supply]

    config = {
        'name': 'unique_model_run_name',
        'stamp': '2017-09-20T12:53:23+00:00',
        'description': 'a description of what the model run contains',
        'timesteps': [2010, 2011, 2012],
        'sos_model': sos_model,
        'scenarios': {
            'climate': 'RCP4.5'
        },
        'narratives': [
            Mock(data={'model_name': {'parameter_name': 0}}),
            Mock(data={'model_name': {'parameter_name': 0}})
        ],
        'strategies': [
            {
                'strategy': 'pre-specified-planning',
                'description': 'build_nuclear',
                'model_name': 'energy_supply',
                'interventions': [
                    {'name': 'nuclear_large', 'build_year': 2012},
                    {'name': 'carrington_retire', 'build_year': 2011}
                ]
            }
        ]
    }
    return config


@fixture(scope='function')
def model_run(config_data):
    """ModelRun built from config
    """
    builder = ModelRunBuilder()
    builder.construct(config_data)
    return builder.finish()


@fixture(scope='function')
def mock_model_run():
    """Minimal mock ModelRun
    """
    sos_model = Mock()
    sos_model.parameters = {}
    sos_model.models = []
    modelrun = Mock()
    modelrun.strategies = []
    modelrun.sos_model = sos_model
    modelrun.narratives = []
    modelrun.model_horizon = [1, 2]
    return modelrun


@fixture(scope='function')
def mock_store():
    """Minimal mock store
    """
    store = Mock()
    store.read_model_run = Mock(return_value={'narratives': {}})
    store.read_strategies = Mock(return_value=[])
    store.read_all_initial_conditions = Mock(return_value=[])

    store.read_sos_model = Mock(return_value={'sector_models': ['sector_model_test']})
    store.read_interventions = Mock(return_value={})

    return store


class TestModelRunBuilder:
    """Build from config
    """
    def test_builder(self, config_data):
        """Test basic properties
        """
        builder = ModelRunBuilder()
        builder.construct(config_data)
        modelrun = builder.finish()

        assert modelrun.name == 'unique_model_run_name'
        assert modelrun.timestamp == '2017-09-20T12:53:23+00:00'
        assert modelrun.model_horizon == [2010, 2011, 2012]
        assert modelrun.status == 'Built'
        assert modelrun.scenarios == {'climate': 'RCP4.5'}
        assert modelrun.narratives == config_data['narratives']
        assert modelrun.strategies == config_data['strategies']

    def test_builder_scenario_sosmodelrun_not_in_sosmodel(self, config_data):
        """Error from unused scenarios
        """
        config_data['scenarios'] = {
            'climate': 'RCP4.5',
            'population': 'high_population'
        }
        builder = ModelRunBuilder()
        builder.construct(config_data)

        with raises(ModelRunError) as ex:
            builder.finish()
        assert "ScenarioSet 'population' is selected in the ModelRun " \
               "configuration but not found in the SosModel configuration" in str(ex)


class TestModelRun:
    """Core ModelRun
    """
    def test_run_static(self, model_run, mock_store):
        """Call run
        """
        model_run.run(mock_store)

    def test_run_timesteps(self, config_data):
        """should error that timesteps are empty
        """
        config_data['timesteps'] = []
        builder = ModelRunBuilder()
        builder.construct(config_data)
        model_run = builder.finish()
        store = Mock()
        with raises(ModelRunError) as ex:
            model_run.run(store)
        assert 'No timesteps specified' in str(ex)

    def test_serialize(self, config_data):
        """Serialise back to config dict
        """
        builder = ModelRunBuilder()
        builder.construct(config_data)
        model_run = builder.finish()

        expected = copy(config_data)
        expected['sos_model'] = config_data['sos_model'].name  # expect a reference by name
        assert expected == model_run.as_dict()


class TestModelRunner():
    """ModelRunner should call into sos_model
    """
    def test_call_before_model_run(self, mock_store, mock_model_run):
        """Call once
        """
        runner = ModelRunner()
        runner.solve_model(mock_model_run, mock_store)
        assert mock_model_run.sos_model.before_model_run.call_count == 1

    def test_call_simulate(self, mock_store, mock_model_run):
        """Call once per timestep
        """
        runner = ModelRunner()
        runner.solve_model(mock_model_run, mock_store)
        assert mock_model_run.sos_model.simulate.call_count == 2