import resqpy.olio.load_data as ld
import pytest


@pytest.mark.skip(reason = "No data yet")
def test_load_corp_array_from_file_corp_bin():
    # Arrange
    filename = ''

    # Act
    corp_data = ld.load_corp_array_from_file(file_name = filename, corp_bin = True)

    # Assert
    pass


@pytest.mark.skip(reason = "No data yet")
def test_load_corp_array_from_file_extent_kji_none():
    # Arrange
    filename = ''

    # Act
    corp_data = ld.load_corp_array_from_file(file_name = filename, extent_kji = None)

    # Assert
    pass


@pytest.mark.skip(reason = "No data yet")
def test_load_array_from_ascii_file_result_none():
    # Arrange
    filename = ''

    # Act
    ascii_data = ld.load_array_from_ascii_file(file_name = filename)

    # Assert
    pass


@pytest.mark.skip(reason = "No data yet")
def test_load_fault_mask():
    # Arrange
    filename = ''

    # Act
    fault_mask = ld.load_fault_mask(file_name = filename)

    # Assert
    pass
