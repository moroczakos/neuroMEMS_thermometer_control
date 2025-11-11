import pytest
import queue
from unittest.mock import MagicMock, patch
from utils.ui_utils.live_plotter import LiveDataPlotter


@pytest.fixture
def plotter():
    mock_canvas = MagicMock()
    mock_axes = MagicMock()
    mock_lines = [MagicMock(), MagicMock()]
    mock_scrollbar = MagicMock()
    mock_logger = MagicMock()
    return LiveDataPlotter(
        canvas = mock_canvas,
        axes = mock_axes,
        lines = mock_lines,
        scrollbar = mock_scrollbar,
        average_count = 1,
        logger = mock_logger,
    )


def test_initial_state(plotter):
    """Verify LiveDataPlotter initializes with correct defaults."""
    assert plotter.get_max_offset() == 0
    assert plotter.get_view_offset() == 0
    assert plotter.max_points_to_plot == 100
    assert plotter.average_count_var == 1
    assert plotter.running is False
    assert isinstance(plotter.data_queue, queue.Queue)


def test_reset_clears_state(plotter):
    """Ensure reset() clears all fields and shuts down executor if present."""
    # Arrange
    mock_exec = MagicMock()
    plotter.executor = mock_exec
    plotter.full_timestamps = [1, 2, 3]
    plotter.running = True

    # Act
    plotter.reset()

    # Assert
    assert plotter.full_timestamps == []
    assert plotter.running is False
    mock_exec.shutdown.assert_called_once_with(wait = False)


def test_start_and_stop_creates_executor(plotter):
    """Ensure start() and stop() control executor lifecycle."""
    with patch("utils.ui_utils.live_plotter.ThreadPoolExecutor", autospec = True) as MockExec:
        mock_exec = MockExec.return_value
        plotter.start()
        assert plotter.running is True
        mock_exec.submit.assert_called_once()

        plotter.stop()
        mock_exec.shutdown.assert_called_once_with(wait = False)
        assert plotter.running is False


def test_enqueue_adds_data(plotter):
    """Check that enqueue() adds items to queue."""
    # Act
    plotter.enqueue(1.0, 2.0, 3.0)

    # Assert
    assert not plotter.data_queue.empty()
    assert plotter.data_queue.get() == (1.0, 2.0, 3.0)


@patch("utils.ui_utils.live_plotter.update_plot")
def test_update_plot_sets_scroll_and_calls_update(update_mock, plotter):
    """Verify scrollbar set and update_plot call work correctly."""
    # Arrange
    plotter.full_timestamps = list(range(10))
    plotter.full_y1_data = [1] * 10
    plotter.full_y2_data = [2] * 10
    plotter.max_points_to_plot = 5
    plotter.view_offset = 2

    # Act
    plotter.update_plot()

    # Assert
    assert plotter.timestamps == plotter.full_timestamps[3:8]
    plotter.scrollbar.set.assert_called()
    update_mock.assert_called_once()


@patch("utils.ui_utils.live_plotter.update_plot")
def test_update_plot_handles_no_data(update_mock, plotter):
    """If no data, scrollbar.set(1.0, 1.0) should be used."""
    # Arrange
    plotter.full_timestamps = []

    # Act
    plotter.update_plot()

    # Assert
    plotter.scrollbar.set.assert_called_once_with(1.0, 1.0)
    update_mock.assert_called_once()


@patch("utils.ui_utils.live_plotter.update_plot")
def test_accumulate_and_plot_triggers_average(update_mock, plotter):
    """When data_counter reaches average_count, append averaged values and reset."""
    # Arrange
    plotter.average_count_var = 2

    # Act & Assert
    plotter._accumulate_and_plot(1, 2, 4)
    assert plotter.data_counter == 1  # still accumulating

    # Second call should trigger average append  reset
    plotter._accumulate_and_plot(2, 4, 6)
    assert plotter.full_timestamps == [2]
    assert plotter.full_y1_data == [3.0]
    assert plotter.full_y2_data == [5.0]
    update_mock.assert_called_once()


def test_accumulate_and_plot_handles_exception(plotter):
    """If exception occurs during update_plot, logger should log error."""
    # Arrange & Act
    plotter.average_count_var = 1
    with patch.object(plotter, "update_plot", side_effect = RuntimeError("fail")):
        plotter._accumulate_and_plot(1, 2, 3)

    # Assert
    args, _ = plotter.logger.call_args
    assert "Plotting error" in args[1]


def test_worker_loop_processes_queue(plotter):
    """Worker loop consumes queue and calls _accumulate_and_plot."""
    # Arrange
    plotter.running = True
    plotter.data_queue.put((1, 2, 3))
    plotter.data_queue.put((4, 5, 6))

    # Act & Assert
    with patch.object(plotter, "_accumulate_and_plot") as mock_accum:
        # stop loop after one pass
        plotter.running = False
        plotter._worker_loop()
        mock_accum.assert_any_call(1, 2, 3)
        mock_accum.assert_any_call(4, 5, 6)
