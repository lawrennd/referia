import referia as rf
import unittest

import pandas as pd


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
        filename = "text.xlsx"
        details = {
            "filename": "test.xlsx",
            "directory": ".",
            "header": 0,
            "sheet": "Sheet1",
        }
        data = pd.DataFrame(rf.fake.rows(30))
        rf.access.write_excel(data, details)
        read_data = rf.access.read_excel(details)
        diff = data.compare(read_data)
        self.assertTrue(len(diff.index)==0)

    def test_write_read_excel(self):
        """test_write_read_excel: test the write to and read from an excel spreadsheet."""
        details = {
            "filename": "test.xlsx",
            "directory": ".",
            "header": 0,
            "sheet": "Sheet1",
        }
        data = pd.DataFrame(rf.fake.rows(30))
        rf.access.write_excel(data, details)
        read_data = rf.access.read_excel(details)
        self.assertTrue(read_data.to_dict("records")==data.to_dict("records"))

    def test_write_read_yaml(self):
        """test_write_read_yaml: test the write to and read from an yaml file."""
        details = {
            "filename": "test.yaml",
            "directory": ".",
        }
        data = pd.DataFrame(rf.fake.rows(30))
        rf.access.write_yaml(data, details)
        read_data = rf.access.read_yaml(details)
        self.assertTrue(read_data.to_dict("records")==data.to_dict("records"))

    def test_write_read_yaml_directory(self):
        """test_write_read_yaml_directory: test the write to and read from an yaml directory."""
        extension = ".yaml"
        details = {
            "filename": "filename",
            "directory": "yaml_directory",
            "glob": "*" + extension,
        }
        data = pd.DataFrame(rf.fake.rows(30))
        data["filename"] = data["name"]
        for ind in data.index:
            data.at[ind, "filename"] = data.at[ind, "name"] + extension
        rf.access.write_yaml_directory(data, details)
        read_data = rf.access.read_yaml_directory(details)
        self.assertTrue(read_data.to_dict("records")==data.to_dict("records"))

    def test_write_read_markdown_directory(self):
        """test_write_read_markdown_directory: test the write to and read from an markdown directory."""
        extension = ".md"
        details = {
            "filename": "filename",
            "directory": "markdown_directory",
            "glob": "*" + extension,
        }
        data = pd.DataFrame(rf.fake.rows(30))
        data["filename"] = data["name"]
        for ind in data.index:
            data.at[ind, "filename"] = data.at[ind, "name"] + extension
        rf.access.write_markdown_directory(data, details)
        read_data = rf.access.read_markdown_directory(details)
        self.assertTrue(read_data.to_dict("records")==data.to_dict("records"))
        
