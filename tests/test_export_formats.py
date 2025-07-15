#!/usr/bin/env python3
"""
Test script for CSV and HTML export functionality
"""

import os
import tempfile
from build_check import BuildTool, JavaVersion, PluginVersion

class MockAnalyzer:
    """Mock analyzer for testing export functions without GitHub connection"""
    
    def export_csv_report(self, all_build_tools, all_java_versions, all_plugin_versions, output_file, org_name, analysis_mode, total_repos, api_calls, max_workers):
        """Export analysis results to CSV format"""
        import csv
        try:
            with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                
                # Write header
                writer.writerow(['Repository', 'Type', 'Name', 'Version', 'Source Compatibility', 'Target Compatibility', 'Config File', 'Detection Method'])
                
                # Write build tools
                for tool in all_build_tools:
                    writer.writerow([
                        tool.repository,
                        'Build Tool',
                        tool.name,
                        tool.version,
                        '',  # No source compatibility for build tools
                        '',  # No target compatibility for build tools
                        tool.file_path,
                        tool.detection_method
                    ])
                
                # Write Java versions
                for java in all_java_versions:
                    writer.writerow([
                        java.repository,
                        'Java Version',
                        'Java',
                        java.version,
                        java.source_compatibility,
                        java.target_compatibility,
                        java.file_path,
                        java.detection_method
                    ])
                
                # Write plugin versions
                for plugin in all_plugin_versions:
                    writer.writerow([
                        plugin.repository,
                        'Plugin Version',
                        plugin.plugin_name,
                        plugin.version,
                        '',  # No source compatibility for plugins
                        '',  # No target compatibility for plugins
                        plugin.file_path,
                        plugin.detection_method
                    ])
            
            print(f"✅ CSV report saved to: {output_file}")
            
        except Exception as e:
            print(f"❌ Error saving CSV report: {str(e)}")

    def export_html_report(self, all_build_tools, all_java_versions, all_plugin_versions, output_file, org_name, analysis_mode, total_repos, api_calls, max_workers):
        """Export analysis results to HTML format"""
        import time
        try:
            # Generate HTML content
            html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>BuildCheck Report - {org_name}</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            line-height: 1.6;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            padding: 30px;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        h1 {{
            color: #2c3e50;
            border-bottom: 3px solid #3498db;
            padding-bottom: 10px;
        }}
        h2 {{
            color: #34495e;
            margin-top: 30px;
        }}
        .summary-stats {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin: 20px 0;
        }}
        .stat-card {{
            background: #ecf0f1;
            padding: 20px;
            border-radius: 6px;
            text-align: center;
        }}
        .stat-number {{
            font-size: 2em;
            font-weight: bold;
            color: #3498db;
        }}
        .stat-label {{
            color: #7f8c8d;
            margin-top: 5px;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
            background: white;
        }}
        th, td {{
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }}
        th {{
            background-color: #3498db;
            color: white;
            font-weight: bold;
        }}
        tr:nth-child(even) {{
            background-color: #f8f9fa;
        }}
        tr:hover {{
            background-color: #e3f2fd;
        }}
        .version-badge {{
            background: #27ae60;
            color: white;
            padding: 4px 8px;
            border-radius: 12px;
            font-size: 0.9em;
            font-weight: bold;
        }}
        .repo-name {{
            font-family: 'Courier New', monospace;
            background: #f1f2f6;
            padding: 2px 6px;
            border-radius: 4px;
        }}
        .analysis-mode {{
            background: #e8f5e8;
            border: 1px solid #27ae60;
            padding: 10px;
            border-radius: 6px;
            margin: 20px 0;
        }}
        .timestamp {{
            color: #7f8c8d;
            font-size: 0.9em;
            text-align: center;
            margin-top: 30px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🔍 BuildCheck Analysis Report</h1>
        <div class="analysis-mode">
            <strong>Organization:</strong> {org_name}<br>
            <strong>Analysis Mode:</strong> {analysis_mode}<br>
            <strong>Generated:</strong> {time.strftime('%Y-%m-%d %H:%M:%S')}
        </div>
        
        <div class="summary-stats">
            <div class="stat-card">
                <div class="stat-number">{total_repos}</div>
                <div class="stat-label">Repositories Analyzed</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{len(all_build_tools)}</div>
                <div class="stat-label">Build Tools Found</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{len(all_java_versions)}</div>
                <div class="stat-label">Java Versions Found</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{len(all_plugin_versions)}</div>
                <div class="stat-label">Plugin Versions Found</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{api_calls}</div>
                <div class="stat-label">API Calls Made</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{max_workers}</div>
                <div class="stat-label">Parallel Workers</div>
            </div>
        </div>"""
            
            # Add build tools section
            if all_build_tools:
                html_content += f"""
        <h2>🛠️ Build Tool Versions</h2>
        <table>
            <thead>
                <tr>
                    <th>Repository</th>
                    <th>Build Tool</th>
                    <th>Version</th>
                    <th>Config File</th>
                    <th>Detection Method</th>
                </tr>
            </thead>
            <tbody>"""
                
                for tool in all_build_tools:
                    html_content += f"""
                <tr>
                    <td><span class="repo-name">{tool.repository}</span></td>
                    <td><strong>{tool.name.title()}</strong></td>
                    <td><span class="version-badge">{tool.version}</span></td>
                    <td><code>{tool.file_path}</code></td>
                    <td>{tool.detection_method}</td>
                </tr>"""
                
                html_content += """
            </tbody>
        </table>"""
            
            # Add Java versions section
            if all_java_versions:
                html_content += f"""
        <h2>☕ Java Versions</h2>
        <table>
            <thead>
                <tr>
                    <th>Repository</th>
                    <th>Java Version</th>
                    <th>Source Compatibility</th>
                    <th>Target Compatibility</th>
                    <th>Config File</th>
                    <th>Detection Method</th>
                </tr>
            </thead>
            <tbody>"""
                
                for java in all_java_versions:
                    html_content += f"""
                <tr>
                    <td><span class="repo-name">{java.repository}</span></td>
                    <td><span class="version-badge">{java.version}</span></td>
                    <td>{java.source_compatibility or '-'}</td>
                    <td>{java.target_compatibility or '-'}</td>
                    <td><code>{java.file_path}</code></td>
                    <td>{java.detection_method}</td>
                </tr>"""
                
                html_content += """
            </tbody>
        </table>"""
            
            # Add plugin versions section
            if all_plugin_versions:
                html_content += f"""
        <h2>🔌 Plugin Versions</h2>
        <table>
            <thead>
                <tr>
                    <th>Repository</th>
                    <th>Plugin Name</th>
                    <th>Version</th>
                    <th>Config File</th>
                    <th>Detection Method</th>
                </tr>
            </thead>
            <tbody>"""
                
                for plugin in all_plugin_versions:
                    html_content += f"""
                <tr>
                    <td><span class="repo-name">{plugin.repository}</span></td>
                    <td><strong>{plugin.plugin_name}</strong></td>
                    <td><span class="version-badge">{plugin.version}</span></td>
                    <td><code>{plugin.file_path}</code></td>
                    <td>{plugin.detection_method}</td>
                </tr>"""
                
                html_content += """
            </tbody>
        </table>"""
            
            # Close HTML
            html_content += f"""
        <div class="timestamp">
            Report generated by BuildCheck on {time.strftime('%Y-%m-%d at %H:%M:%S')}
        </div>
    </div>
</body>
</html>"""
            
            # Write HTML file
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            print(f"✅ HTML report saved to: {output_file}")
            
        except Exception as e:
            print(f"❌ Error saving HTML report: {str(e)}")

def test_export_formats():
    """Test CSV and HTML export functionality"""
    
    # Create sample data
    build_tools = [
        BuildTool(
            name="maven",
            version="3.8.1",
            file_path=".mvn/wrapper/maven-wrapper.properties",
            repository="test-repo-1",
            branch="main",
            detection_method="Found in .mvn/wrapper/maven-wrapper.properties"
        ),
        BuildTool(
            name="gradle",
            version="7.3.3",
            file_path="gradle/wrapper/gradle-wrapper.properties",
            repository="test-repo-2",
            branch="main",
            detection_method="Found in gradle/wrapper/gradle-wrapper.properties"
        )
    ]
    
    java_versions = [
        JavaVersion(
            version="11",
            source_compatibility="11",
            target_compatibility="11",
            file_path="pom.xml",
            repository="test-repo-1",
            branch="main",
            detection_method="Found in pom.xml"
        ),
        JavaVersion(
            version="17",
            source_compatibility="17",
            target_compatibility="17",
            file_path="build.gradle",
            repository="test-repo-2",
            branch="main",
            detection_method="Found in build.gradle"
        )
    ]
    
    plugin_versions = [
        PluginVersion(
            plugin_name="publishPluginVersion",
            version="1.2.3",
            file_path="gradle.properties",
            repository="test-repo-2",
            branch="main",
            detection_method="Found in gradle.properties"
        )
    ]
    
    # Create mock analyzer instance
    analyzer = MockAnalyzer()
    
    # Test CSV export
    with tempfile.NamedTemporaryFile(suffix='.csv', delete=False) as f:
        csv_file = f.name
    
    try:
        analyzer.export_csv_report(
            build_tools, java_versions, plugin_versions,
            csv_file, "test-org", "test_analysis", 2, 10, 4
        )
        
        # Verify CSV file was created and has content
        assert os.path.exists(csv_file)
        with open(csv_file, 'r') as f:
            content = f.read()
            assert 'Repository' in content
            assert 'test-repo-1' in content
            assert 'maven' in content
            assert '3.8.1' in content
        
        print("✅ CSV export test passed")
        
    finally:
        if os.path.exists(csv_file):
            os.unlink(csv_file)
    
    # Test HTML export
    with tempfile.NamedTemporaryFile(suffix='.html', delete=False) as f:
        html_file = f.name
    
    try:
        analyzer.export_html_report(
            build_tools, java_versions, plugin_versions,
            html_file, "test-org", "test_analysis", 2, 10, 4
        )
        
        # Verify HTML file was created and has content
        assert os.path.exists(html_file)
        with open(html_file, 'r') as f:
            content = f.read()
            assert '<html' in content
            assert 'BuildCheck Report' in content
            assert 'test-repo-1' in content
            assert 'maven' in content
            assert '3.8.1' in content
        
        print("✅ HTML export test passed")
        
    finally:
        if os.path.exists(html_file):
            os.unlink(html_file)
    
    print("🎉 All export format tests passed!")

if __name__ == '__main__':
    test_export_formats() 