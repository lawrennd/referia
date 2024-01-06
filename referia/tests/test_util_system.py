import pytest

from referia.util.system import most_recent_screen_shot  

# Test most_recent_screen_shot
def test_most_recent_screen_shot(mocker):
    # Mocking the directory name and file list
    mocker.patch('os.path.expandvars', return_value="/mocked/path/Desktop/")
    mocker.patch('os.listdir', return_value=["Screenshot 2023-12-31 at 12.00.00.png",
                                             "Screenshot 2024-01-01 at 13.00.00.png"])

    result = most_recent_screen_shot()
    assert result == "Screenshot 2024-01-01 at 13.00.00.png"
