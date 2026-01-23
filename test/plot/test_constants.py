import pytest
from ftio.plot.dash_files.constants import graph_mode, id, io_mode, legend_group

"""
Tests for files ftio/plot/dash_files/constants/
"""

def test_graph_mode_constants():
    assert graph_mode.SUM == 'sum'
    assert graph_mode.AVERAGE == 'average'
    assert graph_mode.INDIVIDUAL == 'individual'
    assert len(graph_mode.ALL_MODES) == 3
    assert graph_mode.SUM in graph_mode.ALL_MODES
    assert graph_mode.AVERAGE in graph_mode.ALL_MODES
    assert graph_mode.INDIVIDUAL in graph_mode.ALL_MODES


def test_id_constants():
    assert id.BUTTON_SHOW == 'button-show'
    assert id.CHECKLIST_IO_MODE == 'checklist-io-mode'
    assert id.DIV_SYNC_READ == 'div-sync-read'
    assert id.DIV_SYNC_WRITE == 'div-sync-write'
    assert id.DIV_ASNYC_READ == 'div-async-read'
    assert id.DIV_ASYNC_WRITE == 'div-async-write'
    assert id.DIV_IO_TIME == 'div-io-time'
    assert len(id.DIV_IO_BY_IO_MODE) == 5
    assert id.DROPDOWN_FILE == 'dropdown-file'
    assert id.STORE_FIGURES_ASYNC_READ == 'store-figures-' + io_mode.ASYNC_READ
    assert id.STORE_FIGURES_ASYNC_WRITE == 'store-figures-' + io_mode.ASYNC_WRITE
    assert id.STORE_FIGURES_SYNC_READ == 'store-figures-' + io_mode.SYNC_READ
    assert id.STORE_FIGURES_SYNC_WRITE == 'store-figures-' + io_mode.SYNC_WRITE
    assert id.STORE_FIGURES_TIME == 'store-figures-' + io_mode.TIME
    assert len(id.STORE_FIGURES_BY_IO_MODE) == 5
    assert id.TYPE_DYNAMIC_GRAPH == 'dynamic-graph'
    assert id.TYPE_DYNAMIC_UPDATER_ASYNC_READ == 'dynamic-updater-' + io_mode.ASYNC_READ
    assert id.TYPE_DYNAMIC_UPDATER_ASYNC_WRITE == 'dynamic-updater-' + io_mode.ASYNC_WRITE
    assert id.TYPE_DYNAMIC_UPDATER_SYNC_READ == 'dynamic-updater-' + io_mode.SYNC_READ
    assert id.TYPE_DYNAMIC_UPDATER_SYNC_WRITE == 'dynamic-updater-' + io_mode.SYNC_WRITE
    assert id.TYPE_DYNAMIC_UPDATER_TIME == 'dynamic-updater-' + io_mode.TIME
    assert len(id.TYPE_DYNAMIC_UPDATER_BY_IO_MODE) == 5


def test_io_mode_constants():
    assert io_mode.ASYNC_READ == 'read_async'
    assert io_mode.ASYNC_WRITE == 'write_async'
    assert io_mode.SYNC_READ == 'read_sync'
    assert io_mode.SYNC_WRITE == 'write_sync'
    assert io_mode.TIME == 'time'
    assert len(io_mode.ALL_MODES) == 5
    assert io_mode.ASYNC_WRITE in io_mode.ALL_MODES
    assert io_mode.ASYNC_READ in io_mode.ALL_MODES
    assert io_mode.SYNC_WRITE in io_mode.ALL_MODES
    assert io_mode.SYNC_READ in io_mode.ALL_MODES
    assert io_mode.TIME in io_mode.ALL_MODES
    assert len(io_mode.MODE_STRING_BY_MODE) == 5


def test_legend_group_constants():
    assert legend_group.ACTUAL_AVERAGE == 'actual_average'
    assert legend_group.ACTUAL_SUM == 'actual_sum'
    assert legend_group.ACTUAL_INDIVIDUAL == 'actual_individual'
    assert legend_group.REQUIRED_AVERAGE == 'required_average'
    assert legend_group.REQUIRED_SUM == 'required_sum'
    assert legend_group.REQUIRED_INDIVIDUAL == 'required_individual'
    assert legend_group.ACTUAL_AVERAGE_TITLE == 'Actual average'
    assert legend_group.ACTUAL_SUM_TITLE == 'Actual sum'
    assert legend_group.ACTUAL_INDIVIDUAL_TITLE == 'Actual individual'
    assert legend_group.REQUIRED_AVERAGE_TITLE == 'Required average'
    assert legend_group.REQUIRED_SUM_TITLE == 'Required sum'
    assert legend_group.REQUIRED_INDIVIDUAL_TITLE == 'Required individual'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])