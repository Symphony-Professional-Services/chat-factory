"""
Setup script for chat-factory package.
"""

from setuptools import setup, find_packages

setup(
    name="chat-factory",
    version="0.2.0",
    packages=find_packages(),
    install_requires=[
        "google-cloud-aiplatform>=1.66.0",
        "scipy>=1.13.1",
        "pandas>=2.2.2",
        "pydantic>=2.9.2",
    ],
    python_requires=">=3.10,<3.12",
    author="Sean Koval",
    description="A modular framework for generating synthetic conversations",
)