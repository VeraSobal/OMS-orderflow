import pytest

from ..tasks import create_backup


@pytest.mark.usefixtures('celery_session_app', 'celery_session_worker')
def test_create_backup(mocker):
    mock_open = mocker.patch('builtins.open')
    mock_call_command = mocker.patch('django.core.management.call_command')

    result = create_backup.delay().get(timeout=10)

    assert result['timestamp'] is not None
    assert result['action'] == 'database_backup'
    mock_open.assert_called_once()
    mock_call_command.assert_called_once()
