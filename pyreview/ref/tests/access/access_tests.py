from nose.tools import assert_equals

import ref

def test_loads():
    """Check the outputs and additionals are the same length"""
    df1 = ref.access.outputs()
    df2 = ref.access.additional()
    assert_equals(len(df1), len(df2))
