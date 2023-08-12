import os 
import tempfile
import yaml
import unittest
import pandas as pd

import referia as rf

class TestData(unittest.TestCase):
    # def setUp(self):
    #     # Specify the directory path containing the config files
    #     test_config_directory = 'referia/tests/configs'

    #     # Load all the .yml files in the directory
    #     self.tests = []
    #     path = os.path.join(os.getcwd(), test_config_directory)
    #     for filename in os.listdir(path):
    #         if filename.endswith('.yml'):
    #             config_file_path = os.path.join(path, filename)
    #             with open(config_file_path) as f:
    #                 cf = yaml.safe_load(f)
    #                 cf["filename"] = filename
    #                 cf["directory"] = path 
    #                 self.tests.append(cf)
    #     # Call create_test_methods to generate the test methods
    #     self.create_test_methods()
        
    # def generate_test_method(self, test_name, test_data):
    #     def test_method(self):
    #         # Test implementation using the test data
    #         # Replace this with your actual test logic
    #         self.assertEqual(2 + 2, test_data['expected_result'])

    #     # Set the test method name and docstring
    #     test_method.__name__ = test_name
    #     test_method.__doc__ = test_data['description']

    #     return test_method

    # def create_test_methods(self):
    #     # Iterate through each configuration item and generate a test method
    #     for cf in self.tests:
    #         test_name = "test_" + cf["title"]
    #         test_method = self.generate_test_method(test_name, cf)
    #         setattr(self, test_name, test_method)
    #         self.addTest(self.__class__(test_name))        

    # def test_hello(self):
    #     pass

    def test_global_consts_one(self):
        """Test loading of global constants."""
        directory = "."
        data = rf.assess.Data(user_file="global_consts_one.yml", directory=directory)
        columns = data.columns

        global_variable_one = rf.fake.row()
        rf.access.write_yaml_file(global_variable_one, filename = os.path.join(directory, "global_variables_one.yml"))
        
        global_variable_two = rf.fake.row()
        rf.access.write_yaml_file(global_variable_two, filename = os.path.join(directory, "global_variables_two.yml"))

        expected_columns = ["test_var", "test_var_two"] + list(global_variable_one.keys()) + list(global_variable_two.keys())
        expected_values = ["test_var", "test_var_two"] + list(global_variable_one.values()) + list(global_variable_two.values())
        
        for column, expected in zip(columns, expected_columns):
            self.assertEqual(column, expected)
        
        for column, value in zip(data.columns, expected_values):
            data.set_column(column)
            self.assertEqual(data.get_value(), value)
        

    # def run_allocation_tests_in_directory(self, dir_path):
    #     # Change the working directory to the directory with the test config and data
    #     print(dir_path)
    #     #os.chdir(dir_path)

    #     # Now run all of your tests.
    #     self.check_initialization()
    #     self.check_get_value_method()
    #     self.check_set_value_method()
    #     self.check_get_column_method()
    #     self.check_set_column_method()

    #     # Change the working directory back to the original location at the end
    #     #os.chdir(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))

    # # Define the actual tests here. These tests will be called by run_tests_in_directory.    
    # def check_initialization(self):
    #     self.assertEqual(self.data._index, None)
    #     self.assertEqual(self.data._column, None)
    #     self.assertEqual(self.data._subindex, None)
    #     self.assertEqual(self.data._writeseries, None)
    #     self.assertEqual(self.data._selector, None)
    #     self.assertIsInstance(self.data._computes, list)
    #     #... add other attributes initialization tests ...

    # def check_add_column(self):
    #     # You need to decide what the get_value method should return and test for that
    #     self.data.add_column("")
    #     self.assertEqual(self.data.get_value(), expected_value)

    # def check_get_value_method(self, value):
    #     # Test that the set_value method correctly updates the value
    #     self.assertEqual(self.data.get_value(), value)

    # def check_get_column_method(self, column):
    #     # Similar to get_value
    #     self.assertEqual(self.data.get_column(), column)

    # def check_set_column_method(self, column):
    #     # Similar to set_value
    #     self.data.set_column(column)
    #     self.assertEqual(self.data.get_column(), column)
