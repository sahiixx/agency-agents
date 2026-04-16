from setuptools import find_packages, setup

setup(
    name="jarvis-desktop-assistant",
    version="3.0.0",
    packages=find_packages(include=["jarvis", "jarvis.*"]),
    entry_points={"console_scripts": ["jarvis=jarvis.main:main"]},
)
