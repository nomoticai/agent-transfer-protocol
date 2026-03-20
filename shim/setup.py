"""
AGTP Python Shim — setup configuration
"""
from setuptools import setup, find_packages

setup(
    name="agtp",
    version="0.1.0",
    description="Agent Transfer Protocol (AGTP) Python shim library — AGTP over HTTP",
    long_description=open("README.md", encoding="utf-8").read(),
    long_description_content_type="text/markdown",
    author="Chris Hood",
    author_email="chris@nomotic.ai",
    url="https://github.com/nomoticai/agent-transfer-protocol",
    packages=find_packages(exclude=["tests*", "examples*"]),
    python_requires=">=3.9",
    install_requires=[
        "requests>=2.28.0",
        "flask>=3.0.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0",
            "pytest-flask>=1.2",
        ],
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Internet :: WWW/HTTP",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    keywords="agtp agent-transfer-protocol ai-agents protocol ietf",
)
