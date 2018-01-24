"""Test ModelData
"""
from unittest.mock import MagicMock, Mock

import numpy as np
from pytest import fixture, raises
from smif.data_layer import DataHandle
from smif.data_layer.data_handle import TimestepResolutionError
from smif.metadata import Metadata, MetadataSet
from smif.model.dependency import Dependency
from smif.parameters import ParameterList


@fixture(scope='function')
def mock_store():
    store = Mock()
    store.read_results = MagicMock(return_value=np.array([[1.0]]))
    return store


@fixture(scope='function')
def mock_model():
    model = Mock()
    model.name = 'test_model'
    model.parameters = ParameterList()
    model.parameters.add_parameter(
        {
            'name': 'smart_meter_savings',
            'description': 'The savings from smart meters',
            'absolute_range': (0, 100),
            'suggested_range': (3, 10),
            'default_value': 3,
            'units': '%',
            'parent': None
        }
    )
    regions = Mock()
    regions.name = 'test_regions'
    intervals = Mock()
    intervals.name = 'test_intervals'
    model.inputs = MetadataSet([
        Metadata('test', regions, intervals, 'test_unit')
    ])
    model.outputs = MetadataSet([
        Metadata('test', regions, intervals, 'test_unit')
    ])
    source_model = Mock()
    source_model.name = 'test_source'
    model.deps = {
        'test': Dependency(
            source_model,
            Metadata('test_output', regions, intervals, 'test_unit'),
            Metadata('test', regions, intervals, 'test_unit')
        )
    }
    return model


class TestDataHandle():
    def test_create(self):
        """should be created with a DataInterface
        """
        DataHandle(Mock(), 1, 2015, [2015, 2020], Mock())

    def test_get_data(self, mock_store, mock_model):
        """should allow read access to input data
        """
        data_handle = DataHandle(mock_store, 1, 2015, [2015, 2020], mock_model)
        expected = np.array([[1.0]])
        actual = data_handle.get_data("test")
        assert actual == expected

        mock_store.read_results.assert_called_with(
            1,
            'test_source',  # read from source model
            'test_output',  # using source model output name
            'test_regions',
            'test_intervals',
            2015,
            None,
            None
        )

    def test_get_data_with_square_brackets(self, mock_store, mock_model):
        """should allow dict-like read access to input data
        """
        data_handle = DataHandle(mock_store, 1, 2015, [2015, 2020], mock_model)
        expected = np.array([[1.0]])
        actual = data_handle["test"]
        assert actual == expected

        mock_store.read_results.assert_called_with(
            1,
            'test_source',  # read from source model
            'test_output',  # using source model output name
            'test_regions',
            'test_intervals',
            2015,
            None,
            None
        )

    def test_set_data(self, mock_store, mock_model):
        """should allow write access to output data
        """
        expected = np.array([[1.0]])
        data_handle = DataHandle(mock_store, 1, 2015, [2015, 2020], mock_model)

        data_handle.set_results("test", expected)
        assert data_handle["test"] == expected

        mock_store.write_results.assert_called_with(
            1,
            'test_model',
            'test',
            expected,
            'test_regions',
            'test_intervals',
            2015,
            None,
            None
        )

    def test_set_data_with_square_brackets(self, mock_store, mock_model):
        """should allow dict-like write access to output data
        """
        expected = np.array([[1.0]])
        data_handle = DataHandle(mock_store, 1, 2015, [2015, 2020], mock_model)

        data_handle["test"] = expected
        assert data_handle["test"] == expected

        mock_store.write_results.assert_called_with(
            1,
            'test_model',
            'test',
            expected,
            'test_regions',
            'test_intervals',
            2015,
            None,
            None
        )


class TestDataHandleTimesteps():
    """Test timestep helper properties
    """
    def test_current_timestep(self):
        """should return current timestep
        """
        data_handle = DataHandle(Mock(), 1, 2015, [2015, 2020], Mock())
        assert data_handle.current_timestep == 2015

    def test_base_timestep(self):
        """should return first timestep in list
        """
        data_handle = DataHandle(Mock(), 1, 2015, [2015, 2020], Mock())
        assert data_handle.base_timestep == 2015

    def test_previous_timestep(self):
        """should return previous timestep from list
        """
        data_handle = DataHandle(Mock(), 1, 2020, [2015, 2020], Mock())
        assert data_handle.previous_timestep == 2015

    def test_previous_timestep_error(self):
        """should raise error if there's no previous timestep in the list
        """
        data_handle = DataHandle(Mock(), 1, 2015, [2015, 2020], Mock())
        with raises(TimestepResolutionError) as ex:
            data_handle.previous_timestep
        assert 'no previous timestep' in str(ex)
