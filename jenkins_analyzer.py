#!/usr/bin/env python3
"""
Jenkins-specific analyzer for detailed pipeline analysis
"""

import re
import yaml
from typing import Dict, List, Optional
from dataclasses import dataclass

@dataclass
class JenkinsStage:
    """Represents a Jenkins pipeline stage"""
    name: str
    tools: List[str]
    artifacts: List[str]
    repositories: List[str]

@dataclass
class JenkinsPipeline:
    """Represents a complete Jenkins pipeline"""
    repository: str
    stages: List[JenkinsStage]
    tools_used: List[str]
    artifactory_repos: List[str]

class JenkinsAnalyzer:
    """Specialized analyzer for Jenkins pipelines"""
    
    def __init__(self):
        self.tool_patterns = {
            'maven': [
                r'sh\s+[\'"](mvn|mvnw)[^"\']*[\'"]',
                r'tool\s+[\'"](maven)[\'"]',
                r'withMaven\s*{'
            ],
            'gradle': [
                r'sh\s+[\'"](gradle|gradlew)[^"\']*[\'"]',
                r'tool\s+[\'"](gradle)[\'"]',
                r'withGradle\s*{'
            ],
            'grunt': [
                r'sh\s+[\'"](grunt)[^"\']*[\'"]',
                r'tool\s+[\'"](grunt)[\'"]',
                r'withGrunt\s*{',
                r'grunt\s+--version',
                r'grunt\s+build',
                r'grunt\s+test'
            ],
            'packer': [
                r'sh\s+[\'"](packer)[^"\']*[\'"]',
                r'tool\s+[\'"](packer)[\'"]',
                r'packer\s+build',
                r'packer\s+validate',
                r'packer\s+init',
                r'packer\s+version'
            ],
            'docker': [
                r'sh\s+[\'"](docker)[^"\']*[\'"]',
                r'docker\.build\s*[\'"]([^"\']+)[\'"]',
                r'docker\.withRegistry\s*[\'"]([^"\']+)[\'"]'
            ],
            'npm': [
                r'sh\s+[\'"](npm|yarn)[^"\']*[\'"]',
                r'tool\s+[\'"](nodejs|npm)[\'"]'
            ]
        }
        
        self.artifact_patterns = [
            r'archiveArtifacts\s*[\'"]([^"\']+)[\'"]',
            r'publishArtifacts\s*[\'"]([^"\']+)[\'"]',
            r'artifactoryPublish\s*[\'"]([^"\']+)[\'"]',
            r'grunt\s+build.*?[\'"]([^"\']+)[\'"]',
            r'packer\s+build.*?[\'"]([^"\']+)[\'"]'
        ]
        
        self.repository_patterns = [
            r'repository\s*[\'"]([^"\']+)[\'"]',
            r'artifactory\s*[\'"]([^"\']+)[\'"]',
            r'credentialsId\s*[\'"]([^"\']+)[\'"]',
            r'artifactory_url\s*[\'"]([^"\']+)[\'"]',
            r'artifactory_repo\s*[\'"]([^"\']+)[\'"]'
        ]

    def analyze_jenkinsfile(self, content: str, repository: str) -> JenkinsPipeline:
        """Analyze a Jenkinsfile for tools and artifacts"""
        stages = []
        tools_used = []
        artifactory_repos = []
        
        # Extract stages
        stage_matches = re.findall(r'stage\s*[\'"]([^"\']+)[\'"]\s*{([^}]+)}', content, re.DOTALL)
        
        for stage_name, stage_content in stage_matches:
            stage_tools = self._extract_tools(stage_content)
            stage_artifacts = self._extract_artifacts(stage_content)
            stage_repos = self._extract_repositories(stage_content)
            
            stages.append(JenkinsStage(
                name=stage_name,
                tools=stage_tools,
                artifacts=stage_artifacts,
                repositories=stage_repos
            ))
            
            tools_used.extend(stage_tools)
            artifactory_repos.extend(stage_repos)
        
        # Remove duplicates
        tools_used = list(set(tools_used))
        artifactory_repos = list(set(artifactory_repos))
        
        return JenkinsPipeline(
            repository=repository,
            stages=stages,
            tools_used=tools_used,
            artifactory_repos=artifactory_repos
        )

    def _extract_tools(self, content: str) -> List[str]:
        """Extract build tools from content"""
        tools = []
        for tool_name, patterns in self.tool_patterns.items():
            for pattern in patterns:
                if re.search(pattern, content, re.IGNORECASE):
                    tools.append(tool_name)
                    break
        return tools

    def _extract_artifacts(self, content: str) -> List[str]:
        """Extract artifact patterns from content"""
        artifacts = []
        for pattern in self.artifact_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            artifacts.extend(matches)
        return artifacts

    def _extract_repositories(self, content: str) -> List[str]:
        """Extract repository references from content"""
        repos = []
        for pattern in self.repository_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            repos.extend(matches)
        return repos 