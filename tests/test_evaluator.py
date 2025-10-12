import pytest
from app.service_manager import _evaluate_available

def test_evaluate_available_simple_expressions(mocker):
    mocker.patch("os.path.exists", return_value=True)
    mocker.patch("shutil.which", return_value="/usr/bin/test")

    assert _evaluate_available("exists('/tmp')") is True
    assert _evaluate_available("which('test')") is True
    assert _evaluate_available("exists('/other') and which('thing')") is True

    mocker.patch("os.path.exists", return_value=False)
    assert _evaluate_available("exists('/tmp')") is False
    assert _evaluate_available("exists('/tmp') or which('test')") is True
    assert _evaluate_available("exists('/tmp') and which('test')") is False

def test_evaluate_available_complex_expressions(mocker):
    mocker.patch("os.path.exists", side_effect=lambda p: p == '/path/a')
    mocker.patch("shutil.which", side_effect=lambda p: p == 'tool_b')

    assert _evaluate_available("exists('/path/a') and which('tool_b')") is True
    assert _evaluate_available("exists('/path/a') or which('tool_c')") is True
    assert _evaluate_available("exists('/path/b') or which('tool_b')") is True
    assert _evaluate_available("exists('/path/b') or which('tool_c')") is False
    assert _evaluate_available("(exists('/path/a') and which('tool_b')) or exists('/path/c')") is True

def test_evaluate_available_invalid_syntax(mocker):
    mocker.patch("os.path.exists", return_value=True)
    mocker.patch("shutil.which", return_value=True)

    with pytest.warns(UserWarning, match="Invalid available expression"):
        assert _evaluate_available("exists('/tmp') and or which('test')") is False
    with pytest.warns(UserWarning, match="Invalid available expression"):
        assert _evaluate_available("exists('/tmp') foo which('test')") is False
    with pytest.warns(UserWarning, match="Unsafe or unknown identifier"):
        assert _evaluate_available("eval('1+1')") is False
    with pytest.warns(UserWarning, match="Unsafe or unknown identifier"):
        assert _evaluate_available("os.path.exists('/tmp')") is False
    with pytest.warns(UserWarning, match="Invalid token"):
        assert _evaluate_available("1 + 1") is False

def test_evaluate_available_boolean_input():
    assert _evaluate_available(True) is True
    assert _evaluate_available(False) is False

def test_evaluate_available_empty_and_none_input():
    assert _evaluate_available(None) is True
    assert _evaluate_available("") is True
    assert _evaluate_available("   ") is True