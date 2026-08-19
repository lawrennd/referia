"""
Test coverage for global_consts loading and integration.

These tests document the INTENDED behavior of global_consts, not necessarily
the current behavior. Some tests may fail, which helps identify what needs fixing.

Created as part of backlog item: 2025-12-21_test-global-consts-loading.md
"""

import pytest
import tempfile
import os
import yaml
import pandas as pd
from referia.config.interface import Interface
from referia.assess.data import CustomDataFrame


class TestGlobalConstsBasicLoading:
    """Test basic global_consts loading mechanisms."""
    
    def test_load_from_yaml_file(self):
        """
        Test loading global_consts from a YAML file.
        
        Expected behavior: A YAML file with key-value pairs should be loaded
        as global constants accessible in the data frame.
        """
        tmpdir = tempfile.mkdtemp()
        
        try:
            # Create a constants YAML file
            consts_file = f"{tmpdir}/constants.yml"
            with open(consts_file, 'w') as f:
                yaml.dump({
                    'model': 'gpt-4o-mini',
                    'temperature': 0.3,
                    'max_tokens': 2000,
                    'index': 'config'
                }, f)
            
            # Create main data file (as list of records for input)
            data_file = f"{tmpdir}/data.yml"
            with open(data_file, 'w') as f:
                yaml.dump([{
                    'name': 'Alice',
                    'task': 'review',
                    'index': 'row1'
                }], f)
            
            # Create interface that loads data + global_consts
            config_file = f"{tmpdir}/_referia.yml"
            with open(config_file, 'w') as f:
                f.write(f"""global_consts:
  type: yaml
  filename: constants.yml
  directory: {tmpdir}
  index: index

input:
  type: yaml
  filename: data.yml
  directory: {tmpdir}
  index: index
""")
            
            interface = Interface.from_file(
                user_file="_referia.yml",
                directory=tmpdir
            )
            
            cdf = CustomDataFrame.from_flow(interface)
            
            # Verify data loaded
            assert len(cdf) == 1
            assert 'name' in cdf.columns
            assert cdf.loc['row1', 'name'] == 'Alice'
            
            # Verify global_consts accessible as columns
            # (This is the intended behavior - constants should be accessible)
            assert 'model' in cdf.columns, "global_consts should add columns to data"
            assert cdf.loc['row1', 'model'] == 'gpt-4o-mini'
            assert cdf.loc['row1', 'temperature'] == 0.3
            
        finally:
            import shutil
            shutil.rmtree(tmpdir, ignore_errors=True)
    
    def test_load_from_local_data(self):
        """
        Test loading global_consts from inline data dict.
        
        Expected behavior: Constants defined inline should be accessible
        without requiring external files.
        """
        tmpdir = tempfile.mkdtemp()
        
        try:
            # Create main data file (as list of records for input)
            data_file = f"{tmpdir}/data.yml"
            with open(data_file, 'w') as f:
                yaml.dump([{
                    'name': 'Bob',
                    'task': 'summary',
                    'index': 'row1'
                }], f)
            
            # Create interface with inline global_consts
            config_file = f"{tmpdir}/_referia.yml"
            with open(config_file, 'w') as f:
                f.write(f"""global_consts:
  type: local
  index: index
  data:
    model: claude-3-haiku
    temperature: 0.7
    index: config

input:
  type: yaml
  filename: data.yml
  directory: {tmpdir}
  index: index
""")
            
            interface = Interface.from_file(
                user_file="_referia.yml",
                directory=tmpdir
            )
            
            cdf = CustomDataFrame.from_flow(interface)
            
            # Verify data loaded
            assert len(cdf) == 1
            assert 'name' in cdf.columns
            
            # Verify global_consts accessible
            assert 'model' in cdf.columns
            assert cdf.loc['row1', 'model'] == 'claude-3-haiku'
            assert cdf.loc['row1', 'temperature'] == 0.7
            
        finally:
            import shutil
            shutil.rmtree(tmpdir, ignore_errors=True)
    
    def test_load_empty_globals(self):
        """
        Test loading with empty global_consts.
        
        This is the current minimal test - should continue to work.
        """
        cdf = CustomDataFrame.from_flow(
            Interface(
                {
                    "globals": {
                        "type": "local",
                        "data": {},
                        "index": "index"
                    }
                },
                user_file="test.yml",
                directory="."
            )
        )
        
        assert isinstance(cdf, CustomDataFrame)
        assert cdf.empty


class TestGlobalConstsHstack:
    """Test loading global_consts from multiple sources with hstack."""
    
    def test_hstack_two_yaml_files(self):
        """
        Test combining two YAML files with hstack.
        
        Expected behavior: Multiple configuration sources should be
        combined into a single set of global constants.
        """
        tmpdir = tempfile.mkdtemp()
        
        try:
            # Create first constants file
            consts1_file = f"{tmpdir}/llm_config.yml"
            with open(consts1_file, 'w') as f:
                yaml.dump({
                    'model': 'gpt-4o-mini',
                    'temperature': 0.3,
                    'index': 'config'
                }, f)
            
            # Create second constants file
            consts2_file = f"{tmpdir}/api_config.yml"
            with open(consts2_file, 'w') as f:
                yaml.dump({
                    'max_tokens': 2000,
                    'timeout': 30,
                    'index': 'config'
                }, f)
            
            # Create main data (as list of records for input)
            data_file = f"{tmpdir}/data.yml"
            with open(data_file, 'w') as f:
                yaml.dump([{
                    'name': 'Alice',
                    'index': 'row1'
                }], f)
            
            # Create interface with hstack global_consts
            config_file = f"{tmpdir}/_referia.yml"
            with open(config_file, 'w') as f:
                f.write(f"""global_consts:
  type: hstack
  index: index
  specifications:
    - type: yaml
      filename: llm_config.yml
      directory: {tmpdir}
      index: index
    - type: yaml
      filename: api_config.yml
      directory: {tmpdir}
      index: index

input:
  type: yaml
  filename: data.yml
  directory: {tmpdir}
  index: index
""")
            
            interface = Interface.from_file(
                user_file="_referia.yml",
                directory=tmpdir
            )
            
            cdf = CustomDataFrame.from_flow(interface)
            
            # Verify all constants from both files are accessible
            assert 'model' in cdf.columns, "Should have constants from first file"
            assert 'max_tokens' in cdf.columns, "Should have constants from second file"
            assert cdf.loc['row1', 'model'] == 'gpt-4o-mini'
            assert cdf.loc['row1', 'max_tokens'] == 2000
            assert cdf.loc['row1', 'timeout'] == 30
            
        finally:
            import shutil
            shutil.rmtree(tmpdir, ignore_errors=True)
    
    def test_hstack_with_select(self):
        """
        Test hstack with select parameter.
        
        Expected behavior: Select parameter should filter which
        global_consts are used.
        """
        tmpdir = tempfile.mkdtemp()
        
        try:
            # Create constants file with multiple entries
            consts_file = f"{tmpdir}/configs.yml"
            with open(consts_file, 'w') as f:
                yaml.dump([
                    {'model': 'gpt-4o-mini', 'index': 'dev'},
                    {'model': 'gpt-4o', 'index': 'prod'}
                ], f)
            
            data_file = f"{tmpdir}/data.yml"
            with open(data_file, 'w') as f:
                yaml.dump({'name': 'Alice', 'index': 'row1'}, f)
            
            config_file = f"{tmpdir}/_referia.yml"
            with open(config_file, 'w') as f:
                f.write(f"""global_consts:
  type: yaml
  filename: configs.yml
  directory: {tmpdir}
  index: index
  select: prod

input:
  type: yaml
  filename: data.yml
  directory: {tmpdir}
  index: index
""")
            
            interface = Interface.from_file(
                user_file="_referia.yml",
                directory=tmpdir
            )
            
            cdf = CustomDataFrame.from_flow(interface)
            
            # Should have selected 'prod' configuration
            assert 'model' in cdf.columns
            assert cdf.loc['row1', 'model'] == 'gpt-4o', "Should select 'prod' config"
            
        finally:
            import shutil
            shutil.rmtree(tmpdir, ignore_errors=True)


class TestGlobalConstsIntegration:
    """Test global_consts integration with compute operations."""
    
    @pytest.mark.skip(reason="Top-level compute doesn't auto-execute yet. See backlog: features/2025-12-21_top-level-compute-execution.md")
    def test_access_globals_in_compute_row_args(self):
        """
        Test accessing global_consts values in compute row_args.
        
        Expected behavior: Global constants should be accessible as
        columns that can be referenced in row_args.
        
        NOTE: Compute defined INSIDE 'input' runs during input loading
        (before global_consts load). Solution: Define compute at TOP-LEVEL
        (after all data loads), but this doesn't auto-execute yet.
        
        This test documents the INTENDED behavior once compute execution
        is properly implemented.
        """
        tmpdir = tempfile.mkdtemp()
        
        try:
            data_file = f"{tmpdir}/data.yml"
            with open(data_file, 'w') as f:
                yaml.dump([{
                    'text': 'Sample text',
                    'index': 'row1'
                }], f)
            
            config_file = f"{tmpdir}/_referia.yml"
            with open(config_file, 'w') as f:
                # Compute at TOP-LEVEL (not inside input) so it runs AFTER global_consts load
                f.write(f"""global_consts:
  type: local
  index: index
  data:
    prefix: "[SUMMARY]"
    index: config

input:
  type: yaml
  filename: data.yml
  directory: {tmpdir}
  index: index

compute:
  - field: formatted_text
    function: render_liquid
    args:
      template: "{{{{ prefix }}}} {{{{ text }}}}"
    row_args:
      prefix: prefix
      text: text
""")
            
            interface = Interface.from_file(
                user_file="_referia.yml",
                directory=tmpdir
            )
            
            cdf = CustomDataFrame.from_flow(interface)
            
            # TODO: Need to explicitly trigger compute when it's at top-level
            # cdf.run_compute() or similar
            
            # Verify compute operation used global_const
            assert 'formatted_text' in cdf.columns
            assert '[SUMMARY]' in cdf.loc['row1', 'formatted_text']
            assert 'Sample text' in cdf.loc['row1', 'formatted_text']
            
        finally:
            import shutil
            shutil.rmtree(tmpdir, ignore_errors=True)
    
    def test_globals_persist_across_vstack(self):
        """
        Test that global_consts are available to all rows in vstack.
        
        Expected behavior: When vstacking multiple data sources,
        global constants should be joined to all rows.
        """
        tmpdir = tempfile.mkdtemp()
        
        try:
            # Create two data files (as lists of records for input)
            data1_file = f"{tmpdir}/data1.yml"
            with open(data1_file, 'w') as f:
                yaml.dump([{'name': 'Alice', 'index': 'row1'}], f)
            
            data2_file = f"{tmpdir}/data2.yml"
            with open(data2_file, 'w') as f:
                yaml.dump([{'name': 'Bob', 'index': 'row2'}], f)
            
            config_file = f"{tmpdir}/_referia.yml"
            with open(config_file, 'w') as f:
                f.write(f"""global_consts:
  type: local
  index: index
  data:
    experiment: exp_001
    index: config

input:
  type: vstack
  index: index
  specifications:
    - type: yaml
      filename: data1.yml
      directory: {tmpdir}
      index: index
    - type: yaml
      filename: data2.yml
      directory: {tmpdir}
      index: index
""")
            
            interface = Interface.from_file(
                user_file="_referia.yml",
                directory=tmpdir
            )
            
            cdf = CustomDataFrame.from_flow(interface)
            
            # Verify both rows have global_const
            assert len(cdf) == 2
            assert 'experiment' in cdf.columns
            assert cdf.loc['row1', 'experiment'] == 'exp_001'
            assert cdf.loc['row2', 'experiment'] == 'exp_001'
            
        finally:
            import shutil
            shutil.rmtree(tmpdir, ignore_errors=True)


class TestGlobalConstsErrors:
    """Test error handling for global_consts."""
    
    def test_missing_globals_file_raises_error(self):
        """
        Test that missing global_consts file raises appropriate error.
        
        Expected behavior: Clear error message when file not found.
        """
        tmpdir = tempfile.mkdtemp()
        
        try:
            data_file = f"{tmpdir}/data.yml"
            with open(data_file, 'w') as f:
                yaml.dump({'name': 'Alice', 'index': 'row1'}, f)
            
            config_file = f"{tmpdir}/_referia.yml"
            with open(config_file, 'w') as f:
                f.write(f"""global_consts:
  type: yaml
  filename: nonexistent.yml
  directory: {tmpdir}
  index: index

input:
  type: yaml
  filename: data.yml
  directory: {tmpdir}
  index: index
""")
            
            interface = Interface.from_file(
                user_file="_referia.yml",
                directory=tmpdir
            )
            
            # Should raise clear error about missing file
            with pytest.raises((FileNotFoundError, ValueError)) as exc_info:
                cdf = CustomDataFrame.from_flow(interface)
            
            error_msg = str(exc_info.value).lower()
            assert 'nonexistent.yml' in error_msg or 'file' in error_msg or 'not found' in error_msg
            
        finally:
            import shutil
            shutil.rmtree(tmpdir, ignore_errors=True)
    
    def test_invalid_globals_type_raises_error(self):
        """
        Test that invalid global_consts type raises appropriate error.
        
        Expected behavior: Clear error message for unsupported type.
        """
        tmpdir = tempfile.mkdtemp()
        
        try:
            config_file = f"{tmpdir}/_referia.yml"
            with open(config_file, 'w') as f:
                f.write(f"""global_consts:
  type: invalid_type
  index: index
""")
            
            # Should raise clear error about invalid type
            with pytest.raises((ValueError, KeyError)) as exc_info:
                interface = Interface.from_file(
                    user_file="_referia.yml",
                    directory=tmpdir
                )
                cdf = CustomDataFrame.from_flow(interface)
            
            error_msg = str(exc_info.value).lower()
            assert 'type' in error_msg or 'invalid' in error_msg
            
        finally:
            import shutil
            shutil.rmtree(tmpdir, ignore_errors=True)


class TestGlobalConstsListOfLocal:
    """A YAML list of local global_consts should merge fields, even when row keys differ."""

    def test_list_merges_fields_from_different_row_keys(self):
        """Programme-manager pattern: two local blocks, different data-row indexes."""
        tmpdir = tempfile.mkdtemp()
        try:
            data_file = f"{tmpdir}/data.yml"
            with open(data_file, "w") as f:
                yaml.dump([{"name": "Alice", "index": "row1"}], f)

            config_file = f"{tmpdir}/_referia.yml"
            with open(config_file, "w") as f:
                f.write(f"""global_consts:
  - type: local
    index: index
    select: roleInterview
    data:
    - index: roleInterview
      openingComment: Check that the applicant can hear you.
  - type: local
    index: index
    data:
    - index: programme-manager
      runningOrder: Welcome and introductions

input:
  type: yaml
  filename: data.yml
  directory: {tmpdir}
  index: index
""")

            interface = Interface.from_file(
                user_file="_referia.yml",
                directory=tmpdir,
            )
            cdf = CustomDataFrame.from_flow(interface)

            assert "openingComment" in cdf.columns
            assert "runningOrder" in cdf.columns
            assert cdf.loc["row1", "openingComment"] == "Check that the applicant can hear you."
            assert cdf.loc["row1", "runningOrder"] == "Welcome and introductions"
        finally:
            import shutil
            shutil.rmtree(tmpdir, ignore_errors=True)


class TestGlobalConstsRegression:
    """Test backward compatibility with existing global_consts usage."""
    
    def test_existing_empty_globals_still_works(self):
        """
        Test that the existing pattern (empty globals) still works.
        
        This is a regression test - ensures CIP-0005 didn't break global_consts.
        """
        # This is the existing minimal test - should continue to work
        cdf = CustomDataFrame.from_flow(
            Interface(
                {
                    "globals": {
                        "type": "local",
                        "data": {},
                        "index": "index"
                    }
                },
                user_file="test.yml",
                directory="."
            )
        )
        
        assert isinstance(cdf, CustomDataFrame)
        assert cdf.empty


if __name__ == "__main__":
    # Run the tests
    pytest.main([__file__, "-v", "-s"])

