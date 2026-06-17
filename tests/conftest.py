"""
Shared pytest setup.

On Windows, Spark launches its Python workers via PYSPARK_PYTHON and defaults to
'python3', which does not exist (only python.exe) -> 'CreateProcess error=2' when a
Spark action runs. Pin both to the interpreter running the tests, before any
SparkSession is created. Harmless on Linux/Mac.
"""
import os
import sys

os.environ.setdefault("PYSPARK_PYTHON", sys.executable)
os.environ.setdefault("PYSPARK_DRIVER_PYTHON", sys.executable)