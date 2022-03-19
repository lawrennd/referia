import os 
import tempfile
import unittest
import pandas as pd

import referia as rf


class AccessTests(unittest.TestCase):
    def test_write_read_json(self):
        """access_tests: test the write to and read from a json file."""
        filename = "test.json"
        data = rf.fake.row()
        rf.access.write_json_file(data, filename)
        read_data = rf.access.read_json_file(filename)
        self.assertTrue(data == read_data)

    def test_write_read_yaml(self):
        """access_tests: test the write to and read from a yaml file."""
        filename = "test.yaml"
        data = rf.fake.row()
        rf.access.write_yaml_file(data, filename)
        read_data = rf.access.read_yaml_file(filename)
        self.assertTrue(data == read_data)

    def test_write_read_markdown(self):
        """access_tests: test the write to and read from a yaml headed markdown file."""
        filename = "test.markdown"
        data = rf.fake.row()
        rf.access.write_markdown_file(data, filename)
        read_data = rf.access.read_markdown_file(filename)
        self.assertTrue(data==read_data)
        

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
        equals = read_data.to_dict("records")==data.to_dict("records")
        if not equals:
            print(data.compare(read_data))
        self.assertTrue(equals)
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
        equals = read_data.to_dict("records")==data.to_dict("records")
        if not equals:
            print(data.compare(read_data))
        self.assertTrue(equals)
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
        equals = read_data.to_dict("records")==data.to_dict("records")
        if not equals:
            print(data.compare(read_data))
        self.assertTrue(equals)
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
        equals = read_data.to_dict("records")==data.to_dict("records")
        if not equals:
            print(data.compare(read_data))
        self.assertTrue(equals)
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
            data.at[ind, "sourceRoot"] = "."
        data = data.sort_values(by="sourceFilename").reset_index(drop=True)
        rf.access.write_json_directory(data, details)
        read_data = rf.access.read_json_directory(details)
        equals = read_data.to_dict("records")==data.to_dict("records")
        if not equals:
            print(data.compare(read_data))
        self.assertTrue(equals)
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
            data.at[ind, "sourceRoot"] = "."
        data = data.sort_values(by="sourceFilename").reset_index(drop=True)
        rf.access.write_yaml_directory(data, details)
        read_data = rf.access.read_yaml_directory(details)
        equals = read_data.to_dict("records")==data.to_dict("records")
        if not equals:
            print(data.compare(read_data))
        self.assertTrue(equals)
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
            data.at[ind, "sourceRoot"] = "."
        data = data.sort_values(by="sourceFilename").reset_index(drop=True)
        rf.access.write_markdown_directory(data, details)
        read_data = rf.access.read_markdown_directory(details)
        equals = read_data.to_dict("records")==data.to_dict("records")
        if not equals:
            print(data.compare(read_data))
        self.assertTrue(equals)
        tmpDirectory.cleanup()
