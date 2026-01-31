from rattlesnake.environment.environment_utilities import ControlTypes, environment_long_names
import pytest


# region: environment_long_names
@pytest.mark.parametrize("control_type", [*ControlTypes])
def test_environment_long_names(control_type):
    value = environment_long_names.get(control_type)
    assert value is not None
    assert isinstance(value, str)
    assert value != ""
