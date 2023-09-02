import os
import unittest
import pandas as pd
from unittest.mock import patch, MagicMock, mock_open
from datetime import datetime
from pandas.testing import assert_frame_equal

import tempfile
import unittest

import referia as rf

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
        self.directory_name = '.'
        self.details = {
            "directory": self.directory_name,
            "header": 0,
            }

        self.json_file_name = 'test.json'
        self.json_details = self.details.copy()
        self.json_details["filename"] = self.json_file_name

        self.yaml_file_name = 'test.yaml'
        self.yaml_details = self.details.copy()
        self.yaml_details["filename"] = self.yaml_file_name
        
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

    def test_write_read_yaml(self):
        """access_tests: test the write to and read from a yaml file."""
        filename = "test.yaml"
        data = rf.fake.row()
        rf.access.write_yaml_file(data, filename)
        read_data = rf.access.read_yaml_file(filename)
        self.assertDictEqual(data,read_data)

    def test_write_read_markdown(self):
        """access_tests: test the write to and read from a yaml headed markdown file."""
        filename = "test.markdown"
        data = rf.fake.row()
        rf.access.write_markdown_file(data, filename)
        read_data = rf.access.read_markdown_file(filename)
        self.assertDictEqual(data, read_data)
        

    def compare_data_frames(self, df1, df2):
        """Compare two data frames."""
        #equals = df1.to_dict("records")==df2.to_dict("records")
        #if not equals:
        #    print(df1.compare(df2))
        #result = df.compare(df2)
        self.assertDictEqual(df1.to_dict(),df2.to_dict())
        
    def test_write_read_csv(self):
        """test_write_read_csv: test the write to and read from an csv file."""
        tmpDirectory = tempfile.TemporaryDirectory()
        details = {
            "filename": "test.csv",
            "directory": tmpDirectory.name,
            "header": 0,
            "delimiter": ",",
            "quotechar": "\"",
        }
        data = pd.DataFrame(rf.fake.rows(30))
        rf.access.write_csv(data, details)
        read_data = rf.access.read_csv(details)
        self.compare_data_frames(data, read_data)
        tmpDirectory.cleanup()

    def test_write_read_excel(self):
        """test_write_read_excel: test the write to and read from an excel spreadsheet."""
        tmpDirectory = tempfile.TemporaryDirectory()
        details = {
            "filename": "test.xlsx",
            "directory": tmpDirectory.name,
            "header": 0,
            "sheet": "Sheet1",
        }
        data = pd.DataFrame(rf.fake.rows(30))
        rf.access.write_excel(data, details)
        read_data = rf.access.read_excel(details)
        self.compare_data_frames(data, read_data)
        tmpDirectory.cleanup()

    def test_write_read_json(self):
        """test_write_read_json: test the write to and read from an json file."""
        tmpDirectory = tempfile.TemporaryDirectory()
        details = {
            "filename": "test.json",
            "directory": tmpDirectory.name,
        }
        data = pd.DataFrame(rf.fake.rows(30))
        rf.access.write_json(data, details)
        read_data = rf.access.read_json(details)
        self.compare_data_frames(data, read_data)
        tmpDirectory.cleanup()

    def test_write_read_yaml(self):
        """test_write_read_yaml: test the write to and read from an yaml file."""
        tmpDirectory = tempfile.TemporaryDirectory()
        details = {
            "filename": "test.yaml",
            "directory": tmpDirectory.name,
        }
        data = pd.DataFrame(rf.fake.rows(30))
        rf.access.write_yaml(data, details)
        read_data = rf.access.read_yaml(details)
        self.compare_data_frames(read_data, data)
        tmpDirectory.cleanup()

    def test_write_read_json_directory(self):
        """test_write_read_json_directory: test the write to and read from an json directory."""
        tmpDirectory = tempfile.TemporaryDirectory()
        extension = ".json"
        details = {
            "directory": tmpDirectory.name,
            "source": [
                {
                    "filename": "sourceFilename",
                    "directory": tmpDirectory.name,
                    "glob": "*" + extension,
                },
            ],
        }
        data = pd.DataFrame(rf.fake.rows(30))
        for ind in data.index:
            data.at[ind, "sourceFilename"] = data.at[ind, "name"] + extension
            data.at[ind, "sourceDirectory"] = tmpDirectory.name
            data.at[ind, "sourceRoot"] = "."
        data = data.sort_values(by="sourceFilename").reset_index(drop=True)
        rf.access.write_json_directory(data, details)
        read_data = rf.access.read_json_directory(details)
        self.compare_data_frames(data, read_data)
        tmpDirectory.cleanup()

    def test_write_read_yaml_directory(self):
        """test_write_read_yaml_directory: test the write to and read from an yaml directory."""
        tmpDirectory = tempfile.TemporaryDirectory()
        extension = ".yaml"
        details = {
            "directory": tmpDirectory.name,
            "source": [
                {
                    "filename": "sourceFilename",
                    "directory": tmpDirectory.name,
                    "glob": "*" + extension,
                },
            ],
        }
        data = pd.DataFrame(rf.fake.rows(30))
        for ind in data.index:
            data.at[ind, "sourceFilename"] = data.at[ind, "name"] + extension
            data.at[ind, "sourceDirectory"] = tmpDirectory.name
            data.at[ind, "sourceRoot"] = "."
        data = data.sort_values(by="sourceFilename").reset_index(drop=True)
        rf.access.write_yaml_directory(data, details)
        read_data = rf.access.read_yaml_directory(details)
        self.compare_data_frames(data, read_data)
        tmpDirectory.cleanup()
        
    def test_write_read_markdown_directory(self):
        """test_write_read_markdown_directory: test the write to and read from an markdown directory."""
        tmpDirectory = tempfile.TemporaryDirectory()
        extension = ".md"
        details = {
            "directory": tmpDirectory.name,
            "source": [
                {
                    "filename": "sourceFilename",
                    "directory": tmpDirectory.name,
                    "glob": "*" + extension,
                },
            ],
        }
        data = pd.DataFrame(rf.fake.rows(30))
        for ind in data.index:
            data.at[ind, "sourceFilename"] = data.at[ind, "name"] + extension
            data.at[ind, "sourceDirectory"] = tmpDirectory.name
            data.at[ind, "sourceRoot"] = "."
        data = data.sort_values(by="sourceFilename").reset_index(drop=True)
        rf.access.write_markdown_directory(data, details)
        read_data = rf.access.read_markdown_directory(details)
        self.compare_data_frames(data, read_data)
        tmpDirectory.cleanup()
    
