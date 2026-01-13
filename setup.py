from setuptools import setup, find_packages

with open("requirements.txt") as f:
    requirements = f.read().splitlines()

setup(
    name="ai-mock-interview",
    version="0.1.0",
    packages=find_packages(),
    install_requires=requirements,
    description="An AI-powered mock interview application.",
    python_requires='>=3.10',
)
