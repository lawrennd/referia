import os 
import tempfile
import unittest
import pandas as pd

import referia as rf


class AccessTests(unittest.TestCase):
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
        

    def test_write_read_excel(self):
        """test_write_read_excel: test the write to and read from an excel spreadsheet."""
        tmpDirectory = tempfile.TemporaryDirectory()
        filename = "text.xlsx"
        details = {
            "filename": "test.xlsx",
            "directory": tmpDirectory.name,
            "header": 0,
            "sheet": "Sheet1",
        }
        data = pd.DataFrame(rf.fake.rows(30))
        rf.access.write_excel(data, details)
        read_data = rf.access.read_excel(details)
        diff = data.compare(read_data)
        self.assertTrue(len(diff.index)==0)
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
        self.assertTrue(read_data.to_dict("records")==data.to_dict("records"))
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
        self.assertTrue(read_data.to_dict("records")==data.to_dict("records"))
        tmpDirectory.cleanup()

    def test_write_read_yaml_directory(self):
        """test_write_read_yaml_directory: test the write to and read from an yaml directory."""
        tmpDirectory = tempfile.TemporaryDirectory()
        extension = ".yaml"
        details = {
            "filename": "sourceFilename",
            "directory": tmpDirectory.name,
            "glob": "*" + extension,
        }
        data = pd.DataFrame(rf.fake.rows(30))
        for ind in data.index:
            data.at[ind, "sourceFilename"] = data.at[ind, "name"] + extension
            data.at[ind, "sourceRoot"] = "."
        data = data.sort_values(by="sourceFilename").reset_index(drop=True)
        rf.access.write_yaml_directory(data, details)
        read_data = rf.access.read_yaml_directory(details)
        self.assertTrue(read_data.to_dict("records")==data.to_dict("records"))
        tmpDirectory.cleanup()

    def test_write_read_markdown_directory(self):
        """test_write_read_markdown_directory: test the write to and read from an markdown directory."""
        tmpDirectory = tempfile.TemporaryDirectory()
        extension = ".md"
        details = {
            "filename": "sourceFilename",
            "directory": tmpDirectory.name,
            "glob": "*" + extension,
        }
        data = pd.DataFrame(rf.fake.rows(30))
        for ind in data.index:
            data.at[ind, "sourceFilename"] = data.at[ind, "name"] + extension
            data.at[ind, "sourceRoot"] = "."
        data = data.sort_values(by="sourceFilename").reset_index(drop=True)
        rf.access.write_markdown_directory(data, details)
        read_data = rf.access.read_markdown_directory(details)
        self.assertTrue(read_data.to_dict("records")==data.to_dict("records"))
        tmpDirectory.cleanup()
