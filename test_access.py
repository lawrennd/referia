import os
import unittest
import pandas as pd
from unittest.mock import patch, MagicMock, mock_open
from datetime import datetime
from pandas.testing import assert_frame_equal

from referia.access import (
    read_json, write_json, read_directory, write_directory, read_json_file,
    write_json_file, yaml_prep, read_yaml_meta_file, write_yaml_meta_file,
    read_markdown_file, read_docx_file, write_markdown_file, create_letter,
    write_letter_file
)
from referia.util import extract_full_filename

class TestUtils(unittest.TestCase):
    def setUp(self):
        self.sample_dict = {
            'date': [datetime(2022, 1, 1), datetime(2022, 1, 2)],
            'integer': [1, 2],
            'string': ['test1', 'test2']
        }
        self.sample_df = pd.DataFrame(self.sample_dict)
        self.json_file_name = 'test.json'
        self.directory_name = '.'
        self.details = {
            "directory": self.directory_name,
            "header": 0,
            }
        self.json_details = self.details.copy()
        self.json_details["filename"] = self.json_file_name
        
    @patch('referia.access.read_json_file')
    def test_read_json(self, mocked_read_json_file):
        full_filename = extract_full_filename(self.json_details)
        mocked_read_json_file.return_value = self.sample_dict
        df = read_json(self.json_details)
        mocked_read_json_file.assert_called_once_with(full_filename)
        assert_frame_equal(df, self.sample_df)

    @patch('referia.access.write_json_file')
    def test_write_json(self, mocked_write_json_file):
        full_filename = extract_full_filename(self.json_details)
        write_json(self.sample_df, self.json_details)
        mocked_write_json_file.assert_called_once_with(self.sample_df.to_dict("records"), full_filename, )

    @patch('json.load')
    @patch('builtins.open', new_callable=mock_open)
    def test_read_json_file(self, mocked_open, mocked_json_load):
        full_filename = extract_full_filename(self.json_details)
        with open(full_filename, 'r') as f:
            mocked_json_load.return_value = self.sample_dict
            d = read_json_file(full_filename)
            mocked_json_load.assert_called_once_with(f)
            self.assertDictEqual(d, self.sample_dict)

    @patch('json.dump')
    @patch('builtins.open', new_callable=mock_open)
    def test_write_json_file(self, mocked_open, mocked_json_dump):
        full_filename = extract_full_filename(self.json_details)
        with open(full_filename, 'w') as f:
            write_json_file(self.sample_dict, self.json_details)
            mocked_json_dump.assert_called_once_with(self.sample_dict, f, sort_keys=False)
    # Add similar tests for read_directory, write_directory, read_yaml_meta_file,
    # write_yaml_meta_file, read_markdown_file, read_docx_file, write_markdown_file,
    # create_letter, and write_letter_file here.

    # The test for yaml_prep is a bit tricky, since it involves a complex transformation
    # of the input data. It would be a good idea to split it into several smaller tests,
    # each one verifying a different part of the transformation.


if __name__ == '__main__':
    unittest.main()
