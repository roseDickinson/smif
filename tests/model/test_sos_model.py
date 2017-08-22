# -*- coding: utf-8 -*-

from copy import copy
from unittest.mock import Mock

import numpy as np
from pytest import fixture, raises
from smif.convert.area import get_register as get_region_register
from smif.convert.area import RegionSet
from smif.convert.interval import get_register as get_interval_register
from smif.convert.interval import IntervalSet
from smif.metadata import MetadataSet
from smif.model.composite import Dependency
from smif.model.scenario_model import ScenarioModel
from smif.model.sector_model import SectorModel
from smif.model.sos_model import ModelSet, SosModel, SosModelBuilder

from ..fixtures.water_supply import WaterSupplySectorModel


@fixture(scope='function')
def get_scenario_model_object():

    data = np.array([[[3.]], [[5.]], [[1.]]], dtype=float)
    scenario_model = ScenarioModel('test_scenario_model')
    scenario_model.add_output('raininess',
                              get_region_register().get_entry('LSOA'),
                              get_interval_register().get_entry('annual'),
                              'ml')
    scenario_model.add_data(data, [2010, 2011, 2012])
    return scenario_model


@fixture(scope='function')
def get_sector_model_object(get_empty_sector_model):

    regions = get_region_register()
    intervals = get_interval_register()

    sector_model = get_empty_sector_model('water_supply')

    sector_model.add_input('raininess',
                           regions.get_entry('LSOA'),
                           intervals.get_entry('annual'),
                           'ml')

    sector_model.add_output('cost',
                            regions.get_entry('LSOA'),
                            intervals.get_entry('annual'),
                            'million GBP')

    sector_model.add_output('water',
                            regions.get_entry('LSOA'),
                            intervals.get_entry('annual'),
                            'Ml')

    return sector_model


@fixture(scope='function')
def get_sos_model_object(get_sector_model_object,
                         get_scenario_model_object):

    sos_model = SosModel('test_sos_model')
    sector_model = get_sector_model_object
    scenario_model = get_scenario_model_object
    sos_model.add_model(sector_model)
    sos_model.add_model(scenario_model)
    sos_model.timesteps = scenario_model.timesteps
    sector_model.add_dependency(scenario_model, 'raininess', 'raininess')

    return sos_model


@fixture(scope='function')
def get_sos_model_with_model_dependency():
    sos_model = SosModel('test_sos_model')
    ws = WaterSupplySectorModel('water_supply')
    ws.inputs = [
        {
            'name': 'raininess',
            'spatial_resolution': 'LSOA',
            'temporal_resolution': 'annual',
            'units': 'ml'
        }
    ]

    ws.outputs = [
        {
            'name': 'water',
            'spatial_resolution': 'LSOA',
            'temporal_resolution': 'annual',
            'units': 'Ml'
        },
        {
            'name': 'cost',
            'spatial_resolution': 'LSOA',
            'temporal_resolution': 'annual',
            'units': 'million GBP'
        }
    ]
    ws.interventions = [
        {"name": "water_asset_a", "location": "oxford"},
        {"name": "water_asset_b", "location": "oxford"},
        {"name": "water_asset_c", "location": "oxford"}
    ]
    sos_model.add_model(ws)

    ws2 = WaterSupplySectorModel('water_supply_2')
    ws2.inputs = [
        {
            'name': 'water',
            'spatial_resolution': 'LSOA',
            'temporal_resolution': 'annual',
            'units': 'Ml'
        }
    ]

    sos_model.add_model(ws2)

    return sos_model


@fixture(scope='function')
def get_sos_model_with_summed_dependency(setup_region_data):
    builder = SosModelBuilder()
    builder.load_scenario_models([{
        'name': 'raininess',
        'temporal_resolution': 'annual',
        'spatial_resolution': 'LSOA',
        'units': 'ml'
    }], {
        "raininess": [
            {
                'year': 2010,
                'value': 3,
                'region': 'oxford',
                'interval': 1
            }
        ]
    }, [2010, 2011, 2012])

    sos_model = builder.finish()

    ws = WaterSupplySectorModel('water_supply')
    ws.inputs = [
        {
            'name': 'raininess',
            'spatial_resolution': 'LSOA',
            'temporal_resolution': 'annual',
            'units': 'ml'
        }
    ]
    ws.outputs = [
        {
            'name': 'water',
            'spatial_resolution': 'LSOA',
            'temporal_resolution': 'annual',
            'units': 'Ml'
        }
    ]

    sos_model.add_model(ws)

    ws2 = WaterSupplySectorModel('water_supply_2')
    ws2.inputs = [
        {
            'name': 'raininess',
            'spatial_resolution': 'LSOA',
            'temporal_resolution': 'annual',
            'units': 'ml'
        }
    ]
    ws2.outputs = [
        {
            'name': 'water',
            'spatial_resolution': 'LSOA',
            'temporal_resolution': 'annual',
            'units': 'Ml'
        }
    ]
    sos_model.add_model(ws2)

    ws3 = WaterSupplySectorModel('water_supply_3')
    ws3.inputs = [
        {
            'name': 'water',
            'spatial_resolution': 'LSOA',
            'temporal_resolution': 'annual',
            'units': 'Ml'
        }
    ]
    sos_model.add_model(ws3)

    return sos_model


@fixture(scope='function')
def get_empty_sector_model():

    class EmptySectorModel(SectorModel):

        def initialise(self, initial_conditions):
            pass

        def simulate(self, timestep, data=None):
            return {'output_name': 'some_data', 'timestep': timestep}

        def extract_obj(self, results):
            return 0

    return EmptySectorModel


class TestSosModelProperties():

    def test_model_inputs_property(self, get_sos_model_object):
        sos_model = get_sos_model_object

        expected = {'raininess': 'water_supply'}

        for key, value in expected.items():
            model_inputs = sos_model.models[value].model_inputs
            assert isinstance(model_inputs, MetadataSet)
            assert key in model_inputs.names

    def test_model_outputs_property(self, get_sos_model_object):
        sos_model = get_sos_model_object

        expected = {'cost': 'water_supply'}

        for key, value in expected.items():
            model_outputs = sos_model.models[value].model_outputs
            assert isinstance(model_outputs, MetadataSet)
            assert key in model_outputs.names


class TestSosModel():

    def test_add_dependency(self, get_empty_sector_model):

        sink_model = get_empty_sector_model('sink_model')
        sink_model.add_input('input_name', Mock(), Mock(), 'units')

        source_model = get_empty_sector_model('source_model')
        source_model.add_output('output_name', Mock(), Mock(), 'units')

        sink_model.add_dependency(source_model, 'output_name', 'input_name', lambda x, y: x)

        model_input = sink_model.model_inputs['input_name']
        actual = sink_model.deps['input_name'].get_data(2010, model_input)
        expected = 'some_data'
        assert actual == expected

    def test_timestep_before(self):
        sos_model = SosModel('test')
        sos_model.timesteps = [2010, 2011, 2012]
        assert sos_model.timestep_before(2010) is None
        assert sos_model.timestep_before(2011) == 2010
        assert sos_model.timestep_before(2012) == 2011
        assert sos_model.timestep_before(2013) is None

    def test_timestep_after(self):
        sos_model = SosModel('test')
        sos_model.timesteps = [2010, 2011, 2012]
        assert sos_model.timestep_after(2010) == 2011
        assert sos_model.timestep_after(2011) == 2012
        assert sos_model.timestep_after(2012) is None
        assert sos_model.timestep_after(2013) is None


class TestIterations:

    def test_guess_outputs_zero(self, get_sos_model_object):
        """If no previous timestep has results, guess outputs as zero
        """
        sos_model = get_sos_model_object
        assert sos_model.timesteps == [2010, 2011, 2012]
        ws_model = sos_model.models['water_supply']
        model_set = ModelSet(
            {ws_model},
            sos_model
        )

        results = model_set.guess_results(ws_model, 2010)
        expected = {
            "cost": np.zeros((1, 1)),
            "water": np.zeros((1, 1))
        }
        assert results == expected

    def test_guess_outputs_last_year(self, get_sos_model_object):
        """If a previous timestep has results, guess outputs as identical
        """
        sos_model = get_sos_model_object
        ws_model = sos_model.models['water_supply']
        model_set = ModelSet(
            {ws_model},
            sos_model
        )

        expected = {
            "cost": np.array([[3.14]]),
            "water": np.array([[2.71]])
        }

        # set up data as though from previous timestep simulation
        year_before = sos_model.timestep_before(2011)
        assert year_before == 2010
        sos_model._results[year_before]['water_supply'] = expected

        results = model_set.guess_results(ws_model, 2011)
        assert results == expected

    def test_converged_first_iteration(self, get_sos_model_object):
        """Should not report convergence after a single iteration
        """
        sos_model = get_sos_model_object
        ws_model = sos_model.models['water_supply']
        model_set = ModelSet(
            {ws_model},
            sos_model
        )

        results = model_set.guess_results(ws_model, 2010)
        model_set.iterated_results[ws_model.name] = [results]

        assert not model_set.converged()

    def test_converged_two_identical(self, get_sos_model_object):
        """Should report converged if the last two output sets are identical
        """
        sos_model = get_sos_model_object
        ws_model = sos_model.models['water_supply']
        model_set = ModelSet(
            {ws_model},
            sos_model
        )

        results = model_set.guess_results(ws_model, 2010)
        model_set.iterated_results = {
            "water_supply": [results, results]
        }

        assert model_set.converged()

    def test_run_sequential(self, get_sos_model_object):
        sos_model = get_sos_model_object
        sos_model.simulate(2010)
        sos_model.simulate(2011)
        sos_model.simulate(2012)

    def test_dependency_aggregation(self, get_sos_model_with_summed_dependency):
        sos_model = get_sos_model_with_summed_dependency

        data = {2010: {'decisions': [],
                       'raininess': np.array([[1, 1]]),
                       'water': np.array([2, 2])
                       }
                }

        sos_model.simulate(2010, data)


@fixture(scope='function')
def get_sector_model_config(setup_project_folder, setup_registers):

    path = setup_project_folder
    water_supply_wrapper_path = str(
        path.join(
            'models', 'water_supply', '__init__.py'
        )
    )

    config = {"name": "water_supply",
              "path": water_supply_wrapper_path,
              "classname": "WaterSupplySectorModel",
              "inputs": [{'name': 'raininess',
                          'spatial_resolution': 'LSOA',
                          'temporal_resolution': 'annual',
                          'units': 'ml'
                          }
                         ],
              "outputs": [
                  {
                      'name': 'cost',
                      'spatial_resolution': 'LSOA',
                      'temporal_resolution': 'annual',
                      'units': 'million GBP'
                  },
                  {
                      'name': 'water',
                      'spatial_resolution': 'LSOA',
                      'temporal_resolution': 'annual',
                      'units': 'Ml'
                  }
              ],
              "initial_conditions": [],
              "interventions": [
                  {"name": "water_asset_a", "location": "oxford"},
                  {"name": "water_asset_b", "location": "oxford"},
                  {"name": "water_asset_c", "location": "oxford"},
              ]
              }

    return config


@fixture(scope='function')
def get_sos_model_config(setup_project_folder):

    path = setup_project_folder
    water_supply_wrapper_path = str(
        path.join(
            'models', 'water_supply', '__init__.py'
        )
    )

    config_data = {
        'timesteps': [2010, 2011, 2012],
        'planning': [],
        'dependencies': [],
        'scenario_metadata':
            [{
                'name': 'raininess',
                'temporal_resolution': 'annual',
                'spatial_resolution': 'LSOA',
                'units': 'ml'
            }],
        'scenario_data': {
            'raininess': [
                {
                    'year': 2010,
                    'value': 3,
                    'region': 'oxford',
                    'interval': 1
                },
                {
                    'year': 2011,
                    'value': 5,
                    'region': 'oxford',
                    'interval': 1
                },
                {
                    'year': 2012,
                    'value': 1,
                    'region': 'oxford',
                    'interval': 1
                }
            ]
        },
        "sector_model_data": [
            {
                "name": "water_supply",
                "path": water_supply_wrapper_path,
                "classname": "WaterSupplySectorModel",
                "inputs": [
                    {
                        'name': 'raininess',
                        'spatial_resolution': 'LSOA',
                        'temporal_resolution': 'annual',
                        'units': 'ml'
                    }
                ],
                "outputs": [
                    {
                        'name': 'cost',
                        'spatial_resolution': 'LSOA',
                        'temporal_resolution': 'annual',
                        'units': 'million GBP'
                    },
                    {
                        'name': 'water',
                        'spatial_resolution': 'LSOA',
                        'temporal_resolution': 'annual',
                        'units': 'Ml'
                    }
                ],
                "initial_conditions": [],
                "interventions": [
                    {"name": "water_asset_a", "location": "oxford"},
                    {"name": "water_asset_b", "location": "oxford"},
                    {"name": "water_asset_c", "location": "oxford"}
                ]
            }
        ]
    }

    return config_data


@fixture
def get_sos_model_config_with_dep(get_sos_model_config):

    dependency_config = [{'source_model': 'raininess',
                          'source_model_output': 'raininess',
                          'sink_model': 'water_supply',
                          'sink_model_input': 'raininess'}]

    config_data = get_sos_model_config
    config_data['dependencies'] = dependency_config

    return config_data


@fixture
def get_sos_model_config_with_summed_dependency(get_sos_model_config):

    config = get_sos_model_config

    water_model_two = copy(config['sector_model_data'][0])
    water_model_two['name'] = 'water_supply_two'

    water_model_three = copy(config['sector_model_data'][0])
    water_model_three['name'] = 'water_supply_three'
    water_model_three['inputs'] = [{'name': 'water',
                                    'spatial_resolution': 'LSOA',
                                    'temporal_resolution': 'annual',
                                    'units': 'Ml'}]
    water_model_three['outputs'] = []

    config['dependencies'] = [{'source_model': 'water_supply',
                               'source_model_output': 'water',
                               'sink_model': 'water_supply_three',
                               'sink_model_input': 'water'},
                              {'source_model': 'water_supply_two',
                               'source_model_output': 'water',
                               'sink_model': 'water_supply_three',
                               'sink_model_input': 'water'},
                              {'source_model': 'raininess',
                               'source_model_output': 'raininess',
                               'sink_model': 'water_supply',
                               'sink_model_input': 'raininess'},
                              {'source_model': 'raininess',
                               'source_model_output': 'raininess',
                               'sink_model': 'water_supply_two',
                               'sink_model_input': 'raininess'}]
    config['sector_model_data'].append(water_model_two)
    config['sector_model_data'].append(water_model_three)
    return config


class TestSosModelBuilderComponents():

    def test_construct(self, get_sos_model_config):
        """Test constructing from single dict config
        """
        config = get_sos_model_config
        builder = SosModelBuilder()
        builder.construct(config, config['timesteps'])
        sos_model = builder.finish()

        assert isinstance(sos_model, SosModel)
        assert sos_model.sector_models == ['water_supply']
        assert isinstance(sos_model.models['water_supply'], SectorModel)

    def test_set_max_iterations(self, get_sos_model_config):
        """Test constructing from single dict config
        """
        config = get_sos_model_config
        config['max_iterations'] = 125
        builder = SosModelBuilder()
        builder.construct(config, config['timesteps'])
        sos_model = builder.finish()
        assert sos_model.max_iterations == 125

    def test_set_convergence_absolute_tolerance(self, get_sos_model_config):
        """Test constructing from single dict config
        """
        config = get_sos_model_config
        config['convergence_absolute_tolerance'] = 0.0001
        builder = SosModelBuilder()
        builder.construct(config, [2010, 2011, 2012])
        sos_model = builder.finish()
        assert sos_model.convergence_absolute_tolerance == 0.0001

    def test_set_convergence_relative_tolerance(self, get_sos_model_config):
        """Test constructing from single dict config
        """
        config = get_sos_model_config
        config['convergence_relative_tolerance'] = 0.1
        builder = SosModelBuilder()
        builder.construct(config, [2010, 2011, 2012])
        sos_model = builder.finish()
        assert sos_model.convergence_relative_tolerance == 0.1

    def test_load_models(self):
        pass

    def test_load_scenario_models(self):
        pass

    def test_add_planning(self):
        pass

    def test_data_list_to_array(self):

        data = [
                {
                    'year': 2010,
                    'value': 3,
                    'region': 'oxford',
                    'interval': 1
                },
                {
                    'year': 2011,
                    'value': 5,
                    'region': 'oxford',
                    'interval': 1
                },
                {
                    'year': 2012,
                    'value': 1,
                    'region': 'oxford',
                    'interval': 1
                }
            ]

        builder = SosModelBuilder()

        spatial = builder.region_register.get_entry('LSOA')
        temporal = builder.interval_register.get_entry('annual')

        actual = builder._data_list_to_array('raininess', data,
                                             [2010, 2011, 2012],
                                             spatial, temporal)
        expected = np.array([[[3.]], [[5.]], [[1.]]], dtype=float)
        np.testing.assert_equal(actual, expected)


class TestSosModelBuilder():
    """Tests that the correct SosModel structure is created from a configuration
    dictionary

    {'sector_model_data': [{'name':,
                            'path':,
                            'classname':
                            'initial_conditions':
                            'inputs'
                            'outputs'
                            'interventions':,
                            }],
     'scenario_metadata': [{'name':,
                           'spatial_resolution':,
                           'temporal_resolution':,
                           'units':}],
     'scenario_data': {},
     'planning': [],
     'max_iterations': ,
     'convergence_absolute_tolerance': ,
     'convergence_relative_tolerance': ,
     'dependencies': [{'source_model': ,
                       'source_model_output':,
                       'sink_model':,
                       'sink_model_output': }]}

    """

    def test_builder_interventions(self, get_sos_model_config):

        builder = SosModelBuilder()
        config_data = get_sos_model_config
        builder.construct(config_data, config_data['timesteps'])
        sos_model = builder.finish()

        assert sos_model.sector_models == ['water_supply']
        assert sos_model.intervention_names == [
            "water_asset_a",
            "water_asset_b",
            "water_asset_c"
        ]

    def test_scenarios(self, get_sos_model_config):
        """Test constructing from single dict config
        """
        config = get_sos_model_config
        builder = SosModelBuilder()
        builder.construct(config, [2010, 2011, 2012])
        sos_model = builder.finish()

        assert isinstance(sos_model, SosModel)
        assert sos_model.sector_models == ['water_supply']
        assert isinstance(sos_model.models['water_supply'], SectorModel)
        assert isinstance(sos_model.models['raininess'], ScenarioModel)

        actual = sos_model.models['raininess']._data
        np.testing.assert_equal(actual,
                                np.array([[[3.]], [[5.]], [[1.]]], dtype=float))

    def test_missing_planning_asset(self, get_sos_model_config):
        config = get_sos_model_config
        config["planning"] = [
            {
                "name": "test_intervention",
                "build_date": 2012
            }
        ]
        builder = SosModelBuilder()
        builder.construct(config, [2010, 2011, 2012])

        with raises(AssertionError) as ex:
            builder.finish()
        assert "Intervention 'test_intervention' in planning file not found" in str(
            ex.value)

    def test_scenario_dependency(self, get_sos_model_config, setup_region_data):
        """Expect successful build with dependency on scenario data

        Should raise error if no spatial or temporal sets are defined
        """
        config = get_sos_model_config
        config["sector_model_data"][0]["inputs"] = [
            {
                'name': 'raininess',
                'spatial_resolution': 'blobby',
                'temporal_resolution': 'annual',
                'units': 'ml'
            }
        ]

        builder = SosModelBuilder()
        with raises(ValueError):
            builder.construct(config, [2010, 2011, 2012])

        builder.region_register.register(RegionSet('blobby', setup_region_data['features']))

        interval_data = [
            {
                'id': 'ultra',
                'start': 'P0Y',
                'end': 'P1Y'
            }
        ]
        builder.interval_register.register(IntervalSet('mega', interval_data))
        builder.construct(config, [2010, 2011, 2012])

    def test_simple_dependency(self, get_sos_model_config_with_dep):

        config_data = get_sos_model_config_with_dep

        builder = SosModelBuilder()
        builder.construct(config_data, config_data['timesteps'])
        sos_model = builder.finish()

        sos_model.check_dependencies()
        graph = sos_model.dependency_graph

        scenario = sos_model.models['raininess']

        assert 'water_supply' in sos_model.models
        assert sos_model.models['water_supply'] in graph.nodes()
        deps = sos_model.models['water_supply'].deps
        assert 'raininess' in deps.keys()
        expected = Dependency(scenario, scenario.model_outputs['raininess'])
        assert deps['raininess'] == expected

        assert 'raininess' in sos_model.models
        assert sos_model.models['raininess'] in graph.nodes()

    def test_cyclic_dependencies(self, get_sos_model_config_with_summed_dependency):
        config_data = get_sos_model_config_with_summed_dependency

        builder = SosModelBuilder()

        with raises(NotImplementedError):
            builder.construct(config_data, config_data['timesteps'])
        # sos_model = builder.finish()
        # sos_model.check_dependencies()
        # graph = sos_model.dependency_graph

        # scenario = sos_model.models['raininess']
        # water_one = sos_model.models['water_supply']
        # water_two = sos_model.models['water_supply_two']
        # water_three = sos_model.models['water_supply_three']

        # print(graph.edges())

        # assert (scenario, water_one) in graph.edges()
        # assert (scenario, water_two) in graph.edges()
        # assert (water_one, water_three) in graph.edges()
        # assert (water_two, water_three) in graph.edges()


class TestScenarioModel:

    def test_nest_scenario_data(self, setup_country_data):
        data = {
            "mass": [
                {
                    'year': 2015,
                    'region': 'GB',
                    'interval': 'wet_season',
                    'value': 3
                },
                {
                    'year': 2015,
                    'region': 'GB',
                    'interval': 'dry_season',
                    'value': 5
                },
                {
                    'year': 2015,
                    'region': 'NI',
                    'interval': 'wet_season',
                    'value': 1
                },
                {
                    'year': 2015,
                    'region': 'NI',
                    'interval': 'dry_season',
                    'value': 2
                },
                {
                    'year': 2016,
                    'region': 'GB',
                    'interval': 'wet_season',
                    'value': 4
                },
                {
                    'year': 2016,
                    'region': 'GB',
                    'interval': 'dry_season',
                    'value': 6
                },
                {
                    'year': 2016,
                    'region': 'NI',
                    'interval': 'wet_season',
                    'value': 1
                },
                {
                    'year': 2016,
                    'region': 'NI',
                    'interval': 'dry_season',
                    'value': 2.5
                }
            ]
        }

        expected = np.array([
                # 2015
                [
                    # GB
                    [3, 5],
                    # NI
                    [1, 2]
                ],
                # 2016
                [
                    # GB
                    [4, 6],
                    # NI
                    [1, 2.5]
                ]
            ], dtype=float)

        builder = SosModelBuilder()

        interval_data = [
            {'id': 'wet_season', 'start': 'P0M', 'end': 'P5M'},
            {'id': 'dry_season', 'start': 'P5M', 'end': 'P10M'},
            {'id': 'wet_season', 'start': 'P10M', 'end': 'P1Y'},
        ]
        builder.interval_register.register(
            IntervalSet('seasonal', interval_data))
        builder.region_register.register(
            RegionSet('country', setup_country_data['features']))

        builder.load_scenario_models([{
            'name': 'mass',
            'spatial_resolution': 'country',
            'temporal_resolution': 'seasonal',
            'units': 'kg'
        }], data, [2015, 2016])
        actual = builder.sos_model.models['mass']._data

        print(actual)
        print(expected)
        assert np.allclose(actual, expected)

    def test_scenario_data_defaults(self, setup_region_data):
        data = {
            "length": [
                {
                    'year': 2015,
                    'interval': 1,
                    'value': 3.14,
                    'region': 'oxford'
                }
            ]
        }

        expected = np.array([[[3.14]]])

        builder = SosModelBuilder()
        builder.load_scenario_models([{
            'name': 'length',
            'spatial_resolution': 'LSOA',
            'temporal_resolution': 'annual',
            'units': 'm'
        }], data, [2015])
        assert builder.sos_model.models['length']._data == expected

    def test_scenario_data_missing_year(self, setup_region_data,
                                        ):
        data = {
            "length": [
                {
                    'value': 3.14
                }
            ]
        }

        builder = SosModelBuilder()

        msg = "Scenario data item missing year"
        with raises(ValueError) as ex:
            builder.load_scenario_models([{
                'name': 'length',
                'spatial_resolution': 'LSOA',
                'temporal_resolution': 'annual',
                'units': 'm'
            }], data, [2015])
        assert msg in str(ex.value)

    def test_scenario_data_missing_param_mapping(self):
        data = {
            "length": [
                {
                    'value': 3.14,
                    'year': 2015
                }
            ]
        }

        builder = SosModelBuilder()

        msg = "Parameter 'bla_length' in scenario definitions not registered in scenario data"
        with raises(ValueError) as ex:
            builder.load_scenario_models([{
                'name': 'bla_length',
                'spatial_resolution': 'LSOA',
                'temporal_resolution': 'annual',
                'units': 'm'}],
                data, [2015])
        assert msg in str(ex.value)

    def test_scenario_data_missing_param_region(self, setup_region_data,
                                                ):
        data = {
            "length": [
                {
                    'value': 3.14,
                    'region': 'missing',
                    'interval': 1,
                    'year': 2015
                }
            ]
        }

        builder = SosModelBuilder()

        msg = "Region 'missing' not defined in set 'LSOA' for parameter 'length'"
        with raises(ValueError) as ex:
            builder.load_scenario_models([{
                'name': 'length',
                'spatial_resolution': 'LSOA',
                'temporal_resolution': 'annual',
                'units': 'm'
            }], data, [2015])
        assert msg in str(ex)

    def test_scenario_data_missing_param_interval(self, setup_region_data,
                                                  ):
        data = {
            "length": [
                {
                    'value': 3.14,
                    'region': 'oxford',
                    'interval': 1,
                    'year': 2015
                },
                {
                    'value': 3.14,
                    'region': 'oxford',
                    'interval': 'extra',
                    'year': 2015
                }
            ]
        }

        builder = SosModelBuilder()
        msg = "Interval 'extra' not defined in set 'annual' for parameter 'length'"
        with raises(ValueError) as ex:
            builder.load_scenario_models([{
                'name': 'length',
                'spatial_resolution': 'LSOA',
                'temporal_resolution': 'annual',
                'units': 'm'
            }], data, [2015])
        assert msg in str(ex)

    def test_invalid_units_conversion(self, get_sos_model_object):
        sos_model = get_sos_model_object

        scenario_models = sos_model.scenario_models
        assert scenario_models == ['test_scenario_model']

        scenario = sos_model.models['test_scenario_model']

        scenario.model_outputs['raininess'].units = 'incompatible'

        with raises(NotImplementedError) as ex:
            sos_model.simulate(2010)

        assert "Units conversion not implemented" in str(ex.value)