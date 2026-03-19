from setuptools import setup, find_packages

setup(
    name="financial_fraud_analytics",
    version="0.0.1",
    author="Vedant",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    install_requires=[],
)