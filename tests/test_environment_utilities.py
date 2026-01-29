from rattlesnake.environment.environment_utilities import ControlTypes, environment_long_names


# region: environment_long_names
def test_environment_long_names():
    for control_type in ControlTypes:
        value = environment_long_names.get(control_type)
        assert value is not None
        assert isinstance(value, str)
        assert value != ""
