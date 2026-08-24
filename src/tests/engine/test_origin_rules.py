import pytest

from app.engine.origin_rules import compile_rules, headers_for


def test_empty_rules_returns_no_headers():
    rules = compile_rules({})
    assert headers_for(rules, 2, "https://example.com/file.pdf") == {}


def test_matching_customer_and_url_returns_headers():
    rules = compile_rules(
        {
            "2": {
                "^https://fraser-staging.*": {
                    "addHeader": {"Auth-Bypass-Key": "abc12345"}
                }
            }
        }
    )
    assert headers_for(rules, "2", "https://fraser-staging.example.com/a.pdf") == {
        "Auth-Bypass-Key": "abc12345"
    }


def test_int_customer_matches_string_json_key():
    rules = compile_rules(
        {"2": {"^https://fraser-staging.*": {"addHeader": {"Auth-Bypass-Key": "x"}}}}
    )
    assert headers_for(rules, 2, "https://fraser-staging.example.com/a.pdf") == {
        "Auth-Bypass-Key": "x"
    }


def test_non_matching_url_returns_no_headers():
    rules = compile_rules(
        {"2": {"^https://fraser-staging.*": {"addHeader": {"Auth-Bypass-Key": "x"}}}}
    )
    assert headers_for(rules, 2, "https://other.example.com/a.pdf") == {}


def test_unknown_customer_returns_no_headers():
    rules = compile_rules(
        {"2": {"^https://fraser-staging.*": {"addHeader": {"Auth-Bypass-Key": "x"}}}}
    )
    assert headers_for(rules, 3, "https://fraser-staging.example.com/a.pdf") == {}


def test_multiple_matches_merge_with_later_rules_winning():
    rules = compile_rules(
        {
            "2": {
                "^https://": {"addHeader": {"X-First": "1", "X-Shared": "first"}},
                "^https://fraser-staging.*": {
                    "addHeader": {"X-Second": "2", "X-Shared": "second"}
                },
            }
        }
    )
    assert headers_for(rules, 2, "https://fraser-staging.example.com/a.pdf") == {
        "X-First": "1",
        "X-Second": "2",
        "X-Shared": "second",
    }


def test_unknown_operation_is_ignored_with_warning(caplog):
    with caplog.at_level("WARNING"):
        rules = compile_rules(
            {"2": {"^https://.*": {"rewriteUrl": {"target": "somewhere"}}}}
        )
    assert headers_for(rules, 2, "https://example.com/a.pdf") == {}
    assert "unknown operation rewriteUrl" in caplog.text


def test_invalid_regex_raises_value_error():
    with pytest.raises(ValueError, match="invalid regex"):
        compile_rules({"2": {"^https://(unclosed": {"addHeader": {"X": "1"}}}})


def test_non_dict_url_rules_raises_value_error():
    with pytest.raises(ValueError, match="expected an object of URL regexes"):
        compile_rules({"2": ["not-a-dict"]})


def test_non_dict_operations_raises_value_error():
    with pytest.raises(ValueError, match="expected an object of operations"):
        compile_rules({"2": {"^https://.*": "not-a-dict"}})
