import logging
import re

logger = logging.getLogger(__name__)

KNOWN_OPERATIONS = {"addHeader"}


def compile_rules(raw_rules):
    """Validate ORIGIN_HTTP_RULES config and precompile its regexes.

    Input shape: {customer_id: {url_regex: {operation: {...}}}}
    Output: {customer_id (str): [(compiled_regex, {operation: {...}})]}

    Raises ValueError on malformed structure or invalid regex so that a bad
    configuration fails at startup rather than silently dropping headers.
    """
    compiled = {}
    for customer, url_rules in raw_rules.items():
        if not isinstance(url_rules, dict):
            raise ValueError(
                f"ORIGIN_HTTP_RULES: expected an object of URL regexes "
                f"for customer {customer}, got {type(url_rules).__name__}"
            )
        entries = []
        for pattern, operations in url_rules.items():
            try:
                regex = re.compile(pattern)
            except re.error as error:
                raise ValueError(
                    f"ORIGIN_HTTP_RULES: invalid regex {pattern!r} "
                    f"for customer {customer}: {error}"
                )
            if not isinstance(operations, dict):
                raise ValueError(
                    f"ORIGIN_HTTP_RULES: expected an object of operations "
                    f"for customer {customer}, regex {pattern!r}, "
                    f"got {type(operations).__name__}"
                )
            for operation in operations:
                if operation not in KNOWN_OPERATIONS:
                    logger.warning(
                        f"ORIGIN_HTTP_RULES: ignoring unknown operation {operation} for customer {customer}"
                    )
            entries.append((regex, operations))
        compiled[str(customer)] = entries
    return compiled


def headers_for(rules, customer, url):
    """Return the extra headers to apply for this customer/origin URL.

    Headers from all matching rules are merged; later rules override earlier
    ones on header-name conflict. Returns {} when nothing matches.
    """
    headers = {}
    for regex, operations in rules.get(str(customer), []):
        if regex.search(url):
            headers.update(operations.get("addHeader", {}))
    return headers
