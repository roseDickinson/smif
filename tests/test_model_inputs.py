"""Tests the ModelInputs class
"""
import numpy as np
from fixtures.water_supply import one_input, two_inputs
from numpy.testing import assert_equal
from smif.abstract import ModelInputs


class TestModelInputs:

    def test_one_input_decision_variables(self, one_input):

        inputs = ModelInputs(one_input)
        act_names = inputs.decision_variable_names
        act_initial = inputs.decision_variable_values
        act_bounds = inputs.decision_variable_bounds

        exp_names = np.array(['water treatment capacity'], dtype=str)
        exp_initial = np.array([10], dtype=float)
        exp_bounds = np.array([(0, 20)], dtype=(float, 2))

        assert_equal(act_names, exp_names)
        assert_equal(act_initial, exp_initial)
        assert_equal(act_bounds, exp_bounds)

    def test_two_inputs_decision_variables(self, two_inputs):

        inputs = ModelInputs(two_inputs)
        act_names = inputs.decision_variable_names
        act_initial = inputs.decision_variable_values
        act_bounds = inputs.decision_variable_bounds

        exp_names = np.array(['reservoir pumpiness',
                              'water treatment capacity'], dtype='U30')
        exp_initial = np.array([24.583, 10], dtype=float)
        exp_bounds = np.array([(0, 100), (0, 20)], dtype=(float, 2))

        assert_equal(act_names, exp_names)
        assert_equal(act_initial, exp_initial)
        assert_equal(act_bounds, exp_bounds)

    def test_one_input_parameters(self, one_input):

        inputs = ModelInputs(one_input)
        act_names = inputs.parameter_names
        act_values = inputs.parameter_values
        act_bounds = inputs.parameter_bounds

        exp_names = np.array(['raininess'], dtype='U30')
        exp_values = np.array([3], dtype=float)
        exp_bounds = np.array([(0, 5)], dtype=(float, 2))

        assert_equal(act_names, exp_names)
        assert_equal(act_values, exp_values)
        assert_equal(act_bounds, exp_bounds)
