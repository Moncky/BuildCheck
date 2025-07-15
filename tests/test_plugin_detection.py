import re
import pytest

def plugin_version_patterns():
    return [
        r'publishPluginVersion\s*=\s*([^\s]+)',
        r'publishPluginVersion\s*=\s*[\'"]([^\'"]+)[\'"]'
    ]

def extract_plugin_version(content):
    for pattern in plugin_version_patterns():
        match = re.search(pattern, content, re.IGNORECASE | re.MULTILINE)
        if match:
            value = match.group(1).strip()
            # Remove surrounding quotes if present
            if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
                value = value[1:-1]
            return value
    return None

def test_plugin_version_detection_plain():
    content = """
    # Gradle properties
    org.gradle.jvmargs=-Xmx2048m -Dfile.encoding=UTF-8
    org.gradle.parallel=true
    # Plugin versions
    publishPluginVersion=1.2.3
    otherProperty=value
    """
    assert extract_plugin_version(content) == "1.2.3"

def test_plugin_version_detection_quoted():
    content = 'publishPluginVersion = "4.5.6"'
    assert extract_plugin_version(content) == "4.5.6"

def test_plugin_version_detection_none():
    content = '# No plugin version here\norg.gradle.jvmargs=-Xmx2048m'
    assert extract_plugin_version(content) is None 