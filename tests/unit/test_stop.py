from unittest.mock import MagicMock, patch

import pytest
from lightkube.models.autoscaling_v1 import ScaleSpec
from lightkube.models.meta_v1 import ObjectMeta
from lightkube.resources.apps_v1 import Deployment
from test_utils import FakeApiError

from dss.stop import stop_notebook
from dss.utils import DSS_NAMESPACE


@pytest.fixture
def mock_client() -> MagicMock:
    """
    Fixture to mock the Client class.
    """
    with patch("dss.utils.Client") as mock_client:
        yield mock_client


@pytest.fixture
def mock_logger() -> MagicMock:
    """
    Fixture to mock the logger object.
    """
    with patch("dss.stop.logger") as mock_logger:
        yield mock_logger


def test_stop_notebook_success(
    mock_client: MagicMock,
    mock_logger: MagicMock,
) -> None:
    """
    Test case to verify successful stop_notebook call.
    """
    notebook_name = "test-notebook"
    expected_deployment_scale = Deployment.Scale(
        metadata=ObjectMeta(name=notebook_name, namespace=DSS_NAMESPACE),
        spec=ScaleSpec(replicas=0),
    )

    # Call the function to test
    stop_notebook(notebook_name, mock_client)

    # Assertions
    mock_client.replace.assert_called_once_with(expected_deployment_scale)
    mock_logger.info.assert_called_with(
        f"Stopping the notebook {notebook_name}. Check `dss list` for the status of the notebook."
    )


def test_stop_notebook_not_found(
    mock_client: MagicMock,
    mock_logger: MagicMock,
) -> None:
    """
    Tests case to verify failed stop call when the notebook does not exist.
    """
    notebook_name = "test-notebook"

    mock_client.get.side_effect = FakeApiError(404)

    # Call the function to test
    with pytest.raises(RuntimeError):
        stop_notebook(name=notebook_name, lightkube_client=mock_client)

    # Assert
    mock_logger.debug.assert_called_with(
        f"Failed to stop Notebook. Notebook {notebook_name} does not exist."
    )
    mock_logger.error.assert_called_with(
        f"Failed to stop Notebook. Notebook {notebook_name} does not exist."
    )
    mock_logger.info.assert_called_with("Run 'dss list' to check all notebooks.")


def test_stop_notebook_unexpected_error(
    mock_client: MagicMock,
    mock_logger: MagicMock,
) -> None:
    """
    Tests case to verify failed stop call with ApiError on scaling.
    """
    notebook_name = "test-notebook"

    mock_error = FakeApiError(401)
    mock_client.replace.side_effect = mock_error

    # Call the function to test
    with pytest.raises(RuntimeError):
        stop_notebook(name=notebook_name, lightkube_client=mock_client)

    # Assert
    mock_logger.debug.assert_called_with(
        f"Failed to scale down Deployment {notebook_name}: {mock_error}", exc_info=True
    )
    mock_logger.error.assert_called_with(f"Failed to stop notebook {notebook_name}.")
