"""
Test referia's implicit mapping behavior.

This module tests referia's user-friendly implicit behavior for default mappings
while maintaining strict behavior for non-default mappings.
"""

import pytest
import tempfile
import os
import shutil
import referia.assess.data
import referia.config.interface


class TestReferiaImplicitMappingBehavior:
    """Test referia's implicit mapping behavior."""
    
    def test_default_identity_mapping_override(self):
        """Test that referia allows overriding default identity mappings."""
        import pandas as pd
        
        # Create a CustomDataFrame that mimics referia's behavior
        cdf = referia.assess.data.CustomDataFrame()
        
        # Simulate referia's __init__ behavior - creates identity mappings
        df = pd.DataFrame({'job_title': ['Engineer'], 'name': ['John']})
        cdf._augment_column_names(df)
        
        # Verify identity mappings were created
        assert cdf._name_column_map['job_title'] == 'job_title'
        assert cdf._name_column_map['name'] == 'name'
        
        # Now test that referia allows overriding identity mappings (implicit behavior)
        cdf.update_name_column_map('jobTitle', 'job_title')
        
        # The override should work
        assert cdf._name_column_map['jobTitle'] == 'job_title'
        assert cdf._column_name_map['job_title'] == 'jobTitle'
        # The old identity mapping should be gone
        assert 'job_title' not in cdf._name_column_map or cdf._name_column_map.get('job_title') != 'job_title'
    
    def test_default_camelcase_mapping_override(self):
        """Test that referia allows overriding default camelCase mappings for invalid column names."""
        from lynguine.util.misc import to_camel_case
        
        cdf = referia.assess.data.CustomDataFrame()
        
        # Create a column with invalid variable name
        invalid_column = "What is your name?"
        camel_name = to_camel_case(invalid_column)
        
        # Simulate auto-generation of camelCase mapping
        cdf.update_name_column_map(camel_name, invalid_column)
        
        # Verify camelCase mapping was created
        assert cdf._name_column_map[camel_name] == invalid_column
        assert cdf._column_name_map[invalid_column] == camel_name
        
        # Now test that referia allows overriding camelCase mappings for invalid columns
        cdf.update_name_column_map('Name', invalid_column)
        
        # The override should work
        assert cdf._name_column_map['Name'] == invalid_column
        assert cdf._column_name_map[invalid_column] == 'Name'
        # The old camelCase mapping should be gone
        assert camel_name not in cdf._name_column_map or cdf._name_column_map.get(camel_name) != invalid_column
    
    def test_strict_behavior_for_explicit_mappings(self):
        """Test that referia is strict for non-default mappings."""
        cdf = referia.assess.data.CustomDataFrame()
        
        # Create an explicit mapping (not a default mapping)
        cdf.update_name_column_map('jobTitle', 'job_title')
        
        # Verify the mapping was created
        assert cdf._name_column_map['jobTitle'] == 'job_title'
        assert cdf._column_name_map['job_title'] == 'jobTitle'
        
        # Now try to override with a different name - this should fail (strict behavior)
        with pytest.raises(ValueError, match="Column.*already exists in the name-column map"):
            cdf.update_name_column_map('jobName', 'job_title')
    
    def test_strict_behavior_for_camelcase_explicit_mappings(self):
        """Test that referia is strict for explicit camelCase mappings."""
        cdf = referia.assess.data.CustomDataFrame()
        
        # Create an explicit camelCase mapping for a valid column name
        cdf.update_name_column_map('jobTitle', 'job_title')
        
        # Verify the mapping was created
        assert cdf._name_column_map['jobTitle'] == 'job_title'
        assert cdf._column_name_map['job_title'] == 'jobTitle'
        
        # Now try to override - this should fail because it's not a default mapping
        with pytest.raises(ValueError, match="Column.*already exists in the name-column map"):
            cdf.update_name_column_map('jobName', 'job_title')
    
    def test_integration_with_real_scenario(self):
        """Test the integration scenario that was originally failing."""
        tmpdir = tempfile.mkdtemp()
        
        try:
            # Create test data
            people_dir = f"{tmpdir}/_people"
            os.makedirs(people_dir)
            
            with open(f"{people_dir}/john_smith.md", 'w') as f:
                f.write("---\ngiven: John\nfamily: Smith\njob_title: Professor\n---\n")
            
            with open(f"{tmpdir}/_referia.yml", 'w') as f:
                f.write(f"""input:
  type: vstack
  index: Name
  mapping:
    jobTitle: job_title
  specifications:
  - type: markdown_directory
    compute:
      field: Name
      function: render_liquid
      args:
        template: "{{{{ family }}}}_{{{{ given }}}}"
      row_args:
        given: given
        family: family
    source:
    - glob: "*.md"
      directory: {people_dir}/
""")
            
            # Change to test directory
            original_cwd = os.getcwd()
            os.chdir(tmpdir)
            
            try:
                # This should work with referia's implicit behavior
                data = referia.data.Data()
                
                # Verify the data was loaded correctly
                assert len(data) == 1
                assert 'job_title' in data.columns
                
                # Verify the mapping worked correctly
                assert 'jobTitle' in data._name_column_map
                assert data._name_column_map['jobTitle'] == 'job_title'
                assert data._column_name_map['job_title'] == 'jobTitle'
                
                print("✅ Integration test passed - referia handles implicit behavior correctly")
                
            finally:
                os.chdir(original_cwd)
                
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)
    
    def test_is_default_mapping_logic(self):
        """Test the _is_default_mapping helper method."""
        cdf = referia.assess.data.CustomDataFrame()
        
        # Test identity mappings (should be default)
        assert cdf._is_default_mapping('job_title', 'job_title') == True
        
        # Test camelCase mappings for invalid column names (should be default)
        from lynguine.util.misc import to_camel_case, is_valid_var
        invalid_column = "What is your name?"
        camel_name = to_camel_case(invalid_column)
        assert not is_valid_var(invalid_column)  # Verify it's invalid
        assert cdf._is_default_mapping(camel_name, invalid_column) == True
        
        # Test camelCase mappings for valid column names (should NOT be default)
        valid_column = "job_title"
        camel_valid = to_camel_case(valid_column)  # "jobTitle"
        assert is_valid_var(valid_column)  # Verify it's valid
        assert cdf._is_default_mapping(camel_valid, valid_column) == False
        
        # Test explicit mappings (should NOT be default)
        assert cdf._is_default_mapping('jobTitle', 'job_title') == False
        assert cdf._is_default_mapping('customName', 'custom_column') == False


def test_referia_vs_lynguine_behavior():
    """Test that referia and lynguine have different behaviors as intended."""
    import lynguine.assess.data
    import pandas as pd
    
    # Test lynguine (should be strict)
    lynguine_cdf = lynguine.assess.data.CustomDataFrame(data={'job_title': ['Engineer']})
    lynguine_cdf.update_name_column_map('job_title', 'job_title')  # Identity mapping
    
    # lynguine should reject override
    with pytest.raises(ValueError):
        lynguine_cdf.update_name_column_map('jobTitle', 'job_title')
    
    # Test referia (should allow implicit override)
    referia_cdf = referia.assess.data.CustomDataFrame()
    df = pd.DataFrame({'job_title': ['Engineer']})
    referia_cdf._augment_column_names(df)  # Simulate referia's init
    
    # referia should allow override
    referia_cdf.update_name_column_map('jobTitle', 'job_title')
    assert referia_cdf._name_column_map['jobTitle'] == 'job_title'
    
    print("✅ Behavior difference confirmed: lynguine strict, referia implicit")


if __name__ == "__main__":
    # Run the tests
    pytest.main([__file__, "-v"])
