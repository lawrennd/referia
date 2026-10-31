import yaml
import pytest
from referia.config.interface import Interface
from unittest.mock import patch, MagicMock


@pytest.fixture
def sample_data():
    return { "review": [
            {
                "type": "group",
                "children": [
                    {"type": "Checkbox", "field": "test_field1"},
                    {"type": "Checkbox", "field": "test_field2"}
                ]
            },
            {
                "type": "CriterionComment",
                "prefix": "test"
            },
            {
                "type": "load",
                "details": {
                    "filename" : "test_file.yml",
                    "directory": "test_dir",
                    "type" : "yaml"
                }
            },
            {
                "type": "loop",
                "start": 0,
                "stop": 3,
                "body": {"type": "Checkbox", "field": "test_field"}
            },
            {
                "type": "Checkbox",
                "field": "test_field3"
            }
        ]}
def test_interface_initialization(sample_data):
    with patch('referia.config.interface.Interface._expand_review_cluster') as mock_expand:
        mock_expand.return_value = sample_data["review"]  # This line might not be necessary
        interface = Interface(sample_data, directory=".", user_file="test.yml")
        print(mock_expand.call_args)
        mock_expand.assert_called_once_with(sample_data["review"])

def test_expand_review_cluster(sample_data):
    with patch('lynguine.access.io.read_yaml_file') as mock_open:
        # read_yaml_file must return parsed YAML (mapping or sequence of
        # mappings); lynguine converts that to a DataFrame in read_yaml.
        mock_open.return_value = [{"type": "Checkbox", "field": "loaded_field"}]
        expanded = Interface._expand_review_cluster(sample_data['review'])
        
        assert len(expanded) == 5
        assert expanded[0]['type'] == 'group'
        assert expanded[1]['type'] == 'composite'
        assert expanded[2]['type'] == 'load'
        assert expanded[3]['type'] == 'loop'
        assert 'type' in expanded[4]  # Regular widget

def test_expand_group_review():
    with patch('referia.config.interface.expand_group_review') as mock_expand:
        mock_expand.return_value = [{"type": "Checkbox", "field": "test_field"}]
        group = {"type": "group", "children": []}
        expanded = Interface._expand_review_cluster([group])
        assert expanded[0]['type'] == 'group'
        assert 'entries' in expanded[0]
        mock_expand.assert_called_once_with(group)

def test_expand_composite_review():
    with patch('referia.config.interface.expand_composite_review') as mock_expand:
        mock_expand.return_value = [{"type": "Markdown", "field": "test_field"}]
        composite = {"type": "CriterionComment", "prefix": "test"}
        expanded = Interface._expand_review_cluster([composite])
        assert expanded[0]['type'] == 'composite'
        assert 'entries' in expanded[0]
        mock_expand.assert_called_once_with(composite)

def test_expand_load_review():
    with patch('referia.config.interface.expand_load_review') as mock_expand:
        with patch('referia.config.interface.extract_full_filename') as mock_filename:
            mock_expand.return_value = [{"type": "Checkbox", "field": "test_field"}]
            mock_filename.return_value = "full/path/to/test_file.yml"
            load = {
                "type": "load",
                "details": {
                    "file" : "test_file.yml",
                    "directory": "test_dir",
                    "type" : "yaml",
                }
            }
            expanded = Interface._expand_review_cluster([load])
            assert expanded[0]['type'] == 'load'
            assert 'entries' in expanded[0]
            assert expanded[0]['filename'] == "full/path/to/test_file.yml"
            mock_expand.assert_called_once_with(load)
            mock_filename.assert_called_once_with(load["details"])

def test_expand_loop_review():
    loop = {
        "type": "loop",
        "start": 0,
        "stop": 3,
        "body": {"type": "Checkbox", "field": "test_field"}
    }
    expanded = Interface._expand_review_cluster([loop])
    assert expanded[0]['type'] == 'loop'
    assert 'entries' in expanded[0]
    assert expanded[0]['start'] == 0
    assert expanded[0]['stop'] == 3

def test_loop_missing_start():
    loop = {
        "type": "loop",
        "stop": 3,
        "body": {"type": "Checkbox", "field": "test_field"}
    }
    with pytest.raises(ValueError, match="Missing start entry in loop"):
        Interface._expand_review_cluster([loop])

def test_loop_missing_stop():
    loop = {
        "type": "loop",
        "start": 0,
        "body": {"type": "Checkbox", "field": "test_field"}
    }
    with pytest.raises(ValueError, match="Missing stop entry in loop"):
        Interface._expand_review_cluster([loop])

def test_regular_widget():
    widget = {"type": "Checkbox", "field": "test_field"}
    expanded = Interface._expand_review_cluster([widget])
    assert expanded[0] == widget

def test_nested_expansion():
    nested = {
        "type": "group",
        "children": [
            {
                "type": "group",
                "children": [
                    {"type": "Checkbox", "field": "test_field"}
                ]
            }
        ]
    }
    with patch('referia.config.interface.expand_group_review') as mock_expand:
        mock_expand.side_effect = [
            [{"type": "group", "children": [{"type": "Checkbox", "field": "test_field"}]}],
            [{"type": "Checkbox", "field": "test_field"}]
        ]
        expanded = Interface._expand_review_cluster([nested])
        assert expanded[0]['type'] == 'group'
        assert expanded[0]['entries'][0]['type'] == 'group'
        assert mock_expand.call_count == 2

def test_section_preserves_collapse_args():
    section = {
        "type": "Section",
        "title": "Cache",
        "args": {"collapse": False},
        "entries": [
            {"type": "ReloadButton", "field": "_reload"},
        ],
    }
    expanded = Interface._expand_review_cluster([section])
    assert expanded[0]["type"] == "Section"
    assert expanded[0]["title"] == "Cache"
    assert expanded[0]["args"]["collapse"] is False
    assert expanded[0]["entries"][0]["field"] == "_reload"

def test_section_copies_top_level_chrome_flags_into_args():
    section = {
        "type": "Section",
        "title": "Cache",
        "collapse": False,
        "open": True,
        "entries": [
            {"type": "ReloadButton", "field": "_reload"},
        ],
    }
    expanded = Interface._expand_review_cluster([section])
    assert expanded[0]["args"]["collapse"] is False
    assert expanded[0]["args"]["open"] is True


def test_read_yaml_or_empty_markdown_frontmatter(tmp_path):
    path = tmp_path / "_referia.md"
    path.write_text("---\ntitle: Hello\nfoo: 1\n---\nBody\n", encoding="utf-8")
    data = Interface._read_yaml_or_empty(str(path), None, False)
    assert data["title"] == "Hello"
    assert Interface._read_yaml_or_empty(str(path), "title", False) == "Hello"
    with pytest.raises(ValueError, match="not found"):
        Interface._read_yaml_or_empty(str(path), "missing", False)


def test_from_file_falls_back_to_markdown(tmp_path):
    (tmp_path / "_referia.md").write_text(
        "---\ntitle: from md\ninput:\n  type: local\n  index: i\n"
        "  data:\n    - i: 0\n---\n",
        encoding="utf-8",
    )
    with patch.object(Interface, "from_file", wraps=Interface.from_file) as _wrapped:
        pass
    with patch("lynguine.config.interface.Interface.from_file", return_value="ok") as parent:
        result = Interface.from_file(user_file="_referia.yml", directory=str(tmp_path))
        assert result == "ok"
        assert parent.call_args.kwargs["user_file"] == "_referia.md"
    with patch("lynguine.config.interface.Interface.from_file", return_value="ok") as parent:
        Interface.from_file(user_file=None, directory=str(tmp_path))
        assert parent.call_args.kwargs["user_file"] == "_referia.md"
