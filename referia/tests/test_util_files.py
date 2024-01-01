import pytest
from referia.util.files import file_from_re, files_from_re, to_valid_file 

def test_files_from_re(mocker):
    test_directory = "/test/directory"
    test_files = ["file1.txt", "test_file2.txt", "anotherfile.doc"]
    pattern = r".*\.txt"

    mocker.patch('os.listdir', return_value=test_files)

    expected_files = ["/test/directory/file1.txt", "/test/directory/test_file2.txt"]
    assert files_from_re(pattern, test_directory) == expected_files

def test_file_from_re(mocker):
    test_directory = "/test/directory"
    test_files = ["file1.txt", "test_file2.txt", "anotherfile.doc"]
    pattern = r".*\.txt"

    mocker.patch('os.listdir', return_value=test_files)

    expected_file = "/test/directory/file1.txt"
    assert file_from_re(pattern, test_directory) == expected_file

def test_to_valid_file():
    test_cases = {
        "regular_filename.txt": "regular_filename.txt",
        "invalid/\\filename?.txt": "invalid--filename_.txt",
        "unusual::filename**.txt": "unusual__filename__.txt"
    }

    for input_text, expected_output in test_cases.items():
        assert to_valid_file(input_text) == expected_output
