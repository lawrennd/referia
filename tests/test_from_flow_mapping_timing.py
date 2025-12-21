"""
Test coverage for CIP-0005 from_flow() mapping timing approach.

This module tests the proposed architectural fix where:
1. Mappings are NOT created in __init__ 
2. Mappings ARE created after from_flow() completes
3. Explicit interface mappings are applied BEFORE augmentation
4. No timing conflicts between identity and interface mappings

These tests will FAIL with the current implementation (workaround in place)
and should PASS after CIP-0005 proper fix is implemented.
"""

import pytest
import tempfile
import os
import shutil
import pandas as pd
import referia.assess.data
import referia.config.interface


class TestFromFlowMappingTiming:
    """Test the proposed from_flow() mapping timing approach for CIP-0005."""
    
    def test_no_mappings_after_init(self):
        """
        Test that mappings are NOT created in __init__ after CIP-0005 fix.
        
        CIP-0005 IMPLEMENTED: Mappings are no longer created in __init__
        """
        # Create a DataFrame with valid column names
        data = pd.DataFrame({'job_title': ['Engineer'], 'name': ['Alice']})
        
        # Create CustomDataFrame instance
        cdf = referia.assess.data.CustomDataFrame(data=data)
        
        # After CIP-0005 fix: No mappings should exist yet
        assert len(cdf._name_column_map) == 0, \
            "Mappings should not be created in __init__ after CIP-0005 fix"
        assert len(cdf._column_name_map) == 0, \
            "Reverse mappings should not be created in __init__ after CIP-0005 fix"
    
    def test_mappings_exist_after_from_flow(self):
        """
        Test that mappings ARE created after from_flow() completes.
        
        This should work both before and after CIP-0005 implementation.
        """
        tmpdir = tempfile.mkdtemp()
        
        try:
            # Create test data
            test_dir = f"{tmpdir}/data"
            os.makedirs(test_dir)
            
            with open(f"{test_dir}/person.md", 'w') as f:
                f.write("---\ngiven: John\njob_title: Engineer\n---\n")
            
            with open(f"{tmpdir}/_referia.yml", 'w') as f:
                f.write(f"""input:
  type: markdown_directory
  index: sourceFilename
  source:
  - glob: "*.md"
    directory: {test_dir}/
""")
            
            # Load data via from_flow
            interface = referia.config.interface.Interface.from_file(
                user_file="_referia.yml",
                directory=tmpdir
            )
            
            cdf = referia.assess.data.CustomDataFrame.from_flow(interface)
            
            # After from_flow, mappings should exist
            assert len(cdf._name_column_map) > 0, \
                "Mappings should exist after from_flow() completes"
            
            # Verify specific mappings for valid column names (identity mappings)
            assert 'job_title' in cdf._name_column_map
            assert cdf._name_column_map['job_title'] == 'job_title'
            
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)
    
    def test_interface_mapping_precedence(self):
        """
        Test that explicit interface mappings override identity mappings.
        
        This is the key test for CIP-0005's proper fix. The interface mapping
        'jobTitle: job_title' should take precedence over the auto-generated
        identity mapping 'job_title: job_title'.
        
        Current behavior: WORKS (via workaround - allows override)
        Expected after CIP-0005: WORKS (via proper timing - no conflict)
        """
        tmpdir = tempfile.mkdtemp()
        
        try:
            # Create test data
            test_dir = f"{tmpdir}/data"
            os.makedirs(test_dir)
            
            with open(f"{test_dir}/person.md", 'w') as f:
                f.write("---\ngiven: John\njob_title: Engineer\n---\n")
            
            # Interface with explicit mapping
            with open(f"{tmpdir}/_referia.yml", 'w') as f:
                f.write(f"""input:
  type: markdown_directory
  index: sourceFilename
  mapping:
    jobTitle: job_title
  source:
  - glob: "*.md"
    directory: {test_dir}/
""")
            
            interface = referia.config.interface.Interface.from_file(
                user_file="_referia.yml",
                directory=tmpdir
            )
            
            cdf = referia.assess.data.CustomDataFrame.from_flow(interface)
            
            # Verify explicit interface mapping took precedence
            assert 'jobTitle' in cdf._name_column_map, \
                "Interface mapping 'jobTitle' should exist"
            assert cdf._name_column_map['jobTitle'] == 'job_title', \
                "Interface mapping 'jobTitle' should map to 'job_title'"
            
            # Verify identity mapping was NOT created (or was overridden)
            # After CIP-0005: Identity mapping never created (proper timing)
            # Current: Identity mapping overridden (workaround)
            if 'job_title' in cdf._name_column_map:
                # If it exists, it should not be an identity mapping
                assert cdf._name_column_map['job_title'] != 'job_title', \
                    "Identity mapping should not coexist with interface mapping"
            
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)
    
    def test_vstack_with_interface_mappings(self):
        """
        Test vstack with interface-level mappings (the original bug scenario).
        
        This reproduces the scenario from the original bug report where
        vstack with multiple sources and interface mapping 'jobTitle: job_title'
        was causing conflicts.
        """
        tmpdir = tempfile.mkdtemp()
        
        try:
            # Create multiple sources
            source1_dir = f"{tmpdir}/source1"
            source2_dir = f"{tmpdir}/source2"
            os.makedirs(source1_dir)
            os.makedirs(source2_dir)
            
            with open(f"{source1_dir}/person1.md", 'w') as f:
                f.write("---\ngiven: John\nfamily: Smith\njob_title: Professor\n---\n")
            
            with open(f"{source2_dir}/person2.md", 'w') as f:
                f.write("---\ngiven: Jane\nfamily: Doe\njob_title: Engineer\n---\n")
            
            # Vstack with interface-level mapping
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
      directory: {source1_dir}/
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
      directory: {source2_dir}/
""")
            
            interface = referia.config.interface.Interface.from_file(
                user_file="_referia.yml",
                directory=tmpdir
            )
            
            # This should work (currently via workaround, after CIP-0005 via proper timing)
            cdf = referia.assess.data.CustomDataFrame.from_flow(interface)
            
            # Verify data loaded correctly
            assert len(cdf.index) == 2, "Should have 2 records from 2 sources"
            
            # Verify interface mapping applied
            assert 'jobTitle' in cdf._name_column_map
            assert cdf._name_column_map['jobTitle'] == 'job_title'
            
            # Verify index column computed correctly
            assert 'Name' in cdf.index.names
            
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)
    
    def test_computed_index_columns_with_mappings(self):
        """
        Test that computed index columns work correctly with new mapping timing.
        
        This tests a specific concern: index columns computed via liquid templates
        should still work after moving mapping creation to from_flow().
        """
        tmpdir = tempfile.mkdtemp()
        
        try:
            # Create test data
            test_dir = f"{tmpdir}/data"
            os.makedirs(test_dir)
            
            with open(f"{test_dir}/person.md", 'w') as f:
                f.write("---\ngiven: John\nfamily: Smith\njob_title: Engineer\n---\n")
            
            # Interface with computed index and mapping
            with open(f"{tmpdir}/_referia.yml", 'w') as f:
                f.write(f"""input:
  type: markdown_directory
  index: fullName
  mapping:
    jobTitle: job_title
  compute:
    field: fullName
    function: render_liquid
    args:
      template: "{{{{ family }}}}, {{{{ given }}}}"
    row_args:
      given: given
      family: family
  source:
  - glob: "*.md"
    directory: {test_dir}/
""")
            
            interface = referia.config.interface.Interface.from_file(
                user_file="_referia.yml",
                directory=tmpdir
            )
            
            cdf = referia.assess.data.CustomDataFrame.from_flow(interface)
            
            # Verify index was computed correctly
            assert 'fullName' in cdf.index.names
            assert len(cdf.index) > 0
            
            # Verify mappings were applied
            assert 'jobTitle' in cdf._name_column_map
            assert cdf._name_column_map['jobTitle'] == 'job_title'
            
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)
    
    def test_mapping_timing_sequence(self):
        """
        Test that the mapping timing sequence is correct after CIP-0005 fix.
        
        CIP-0005 IMPLEMENTED: Correct sequence is now:
        1. __init__ creates empty mappings
        2. from_flow() calls parent (applies interface mappings)
        3. from_flow() calls _augment_column_names (adds remaining identity mappings)
        4. No conflicts because interface mappings already exist
        """
        tmpdir = tempfile.mkdtemp()
        
        try:
            # Create test data with a column that will get identity mapping
            test_dir = f"{tmpdir}/data"
            os.makedirs(test_dir)
            
            with open(f"{test_dir}/person.md", 'w') as f:
                f.write("---\nname: Alice\njob_title: Engineer\n---\n")
            
            # Interface with mapping for one column, not the other
            with open(f"{tmpdir}/_referia.yml", 'w') as f:
                f.write(f"""input:
  type: markdown_directory
  index: sourceFilename
  mapping:
    jobTitle: job_title
  source:
  - glob: "*.md"
    directory: {test_dir}/
""")
            
            interface = referia.config.interface.Interface.from_file(
                user_file="_referia.yml",
                directory=tmpdir
            )
            
            cdf = referia.assess.data.CustomDataFrame.from_flow(interface)
            
            # After CIP-0005:
            # 1. Interface mapping should exist: jobTitle -> job_title
            assert cdf._name_column_map['jobTitle'] == 'job_title'
            
            # 2. Identity mapping should exist for unmapped column: name -> name
            assert cdf._name_column_map['name'] == 'name'
            
            # 3. No identity mapping for job_title (already mapped via interface)
            assert 'job_title' not in cdf._name_column_map or \
                   cdf._name_column_map['job_title'] != 'job_title'
            
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)


class TestCurrentWorkaroundBehavior:
    """
    Test the current workaround behavior (referia override method).
    
    These tests should PASS with the current implementation and continue
    to PASS after CIP-0005 is implemented (backward compatibility).
    """
    
    def test_workaround_allows_identity_override(self):
        """Test that the current workaround allows overriding identity mappings."""
        cdf = referia.assess.data.CustomDataFrame()
        
        # Simulate __init__ behavior - creates identity mapping
        df = pd.DataFrame({'job_title': ['Engineer']})
        cdf._augment_column_names(df)
        
        # Verify identity mapping exists
        assert cdf._name_column_map['job_title'] == 'job_title'
        
        # Workaround should allow override
        cdf.update_name_column_map('jobTitle', 'job_title')
        
        # Verify override worked
        assert cdf._name_column_map['jobTitle'] == 'job_title'
        assert cdf._column_name_map['job_title'] == 'jobTitle'
    
    def test_workaround_strict_for_explicit_mappings(self):
        """Test that workaround remains strict for explicit mappings."""
        cdf = referia.assess.data.CustomDataFrame()
        
        # Create explicit mapping (not a default)
        cdf.update_name_column_map('jobTitle', 'job_title')
        
        # Try to override - should fail
        with pytest.raises(ValueError, match="Column.*already exists"):
            cdf.update_name_column_map('jobName', 'job_title')
    
    def test_is_default_mapping_helper(self):
        """Test the _is_default_mapping helper method used by workaround."""
        cdf = referia.assess.data.CustomDataFrame()
        
        # Identity mappings are default
        assert cdf._is_default_mapping('job_title', 'job_title') == True
        
        # Explicit mappings are not default
        assert cdf._is_default_mapping('jobTitle', 'job_title') == False
        
        # camelCase for invalid columns are default
        from lynguine.util.misc import to_camel_case
        invalid_col = "What is your name?"
        camel = to_camel_case(invalid_col)
        assert cdf._is_default_mapping(camel, invalid_col) == True


class TestRegressionPrevention:
    """
    Tests to ensure CIP-0005 implementation doesn't break existing functionality.
    
    These should all PASS before and after CIP-0005 implementation.
    """
    
    def test_basic_data_loading(self):
        """Test basic data loading still works."""
        tmpdir = tempfile.mkdtemp()
        
        try:
            test_dir = f"{tmpdir}/data"
            os.makedirs(test_dir)
            
            with open(f"{test_dir}/person.md", 'w') as f:
                f.write("---\nname: Alice\nage: 30\n---\n")
            
            with open(f"{tmpdir}/_referia.yml", 'w') as f:
                f.write(f"""input:
  type: markdown_directory
  index: sourceFilename
  source:
  - glob: "*.md"
    directory: {test_dir}/
""")
            
            interface = referia.config.interface.Interface.from_file(
                user_file="_referia.yml",
                directory=tmpdir
            )
            
            cdf = referia.assess.data.CustomDataFrame.from_flow(interface)
            
            assert len(cdf) == 1
            assert 'name' in cdf.columns
            assert 'age' in cdf.columns
            
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)
    
    def test_multiple_compute_fields(self):
        """Test that multiple compute fields still work."""
        tmpdir = tempfile.mkdtemp()
        
        try:
            test_dir = f"{tmpdir}/data"
            os.makedirs(test_dir)
            
            with open(f"{test_dir}/person.md", 'w') as f:
                f.write("---\ngiven: John\nfamily: Smith\n---\n")
            
            with open(f"{tmpdir}/_referia.yml", 'w') as f:
                f.write(f"""input:
  type: markdown_directory
  index: sourceFilename
  compute:
  - field: fullName
    function: render_liquid
    args:
      template: "{{{{ given }}}} {{{{ family }}}}"
    row_args:
      given: given
      family: family
  - field: initial
    function: render_liquid
    args:
      template: "{{{{ given[0] }}}}{{{{ family[0] }}}}"
    row_args:
      given: given
      family: family
  source:
  - glob: "*.md"
    directory: {test_dir}/
""")
            
            interface = referia.config.interface.Interface.from_file(
                user_file="_referia.yml",
                directory=tmpdir
            )
            
            cdf = referia.assess.data.CustomDataFrame.from_flow(interface)
            
            assert 'fullName' in cdf.columns
            assert 'initial' in cdf.columns
            assert len(cdf) == 1
            
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)


if __name__ == "__main__":
    # Run the tests
    pytest.main([__file__, "-v", "-s"])

