"""
Diagnostic for the Windows Spark setup.
Prints PySpark version, bundled Hadoop version (this decides which winutils you need),
HADOOP_HOME, and whether winutils.exe is found.

Run:  python scripts/check_spark_env.py
"""
import os
from pathlib import Path

from pyspark.sql import SparkSession

spark = (SparkSession.builder.master("local[1]")
         .config("spark.ui.enabled", "false").getOrCreate())
spark.sparkContext.setLogLevel("ERROR")

import pyspark
hadoop_ver = spark.sparkContext._jvm.org.apache.hadoop.util.VersionInfo.getVersion()

print("=" * 55)
print(f"PySpark version        : {pyspark.__version__}")
print(f"Bundled Hadoop version : {hadoop_ver}   <-- match winutils to THIS")
hh = os.environ.get("HADOOP_HOME")
print(f"HADOOP_HOME            : {hh or '(not set)'}")
if hh:
    winutils = Path(hh) / "bin" / "winutils.exe"
    hadoop_dll = Path(hh) / "bin" / "hadoop.dll"
    print(f"winutils.exe found     : {winutils.exists()}  ({winutils})")
    print(f"hadoop.dll found       : {hadoop_dll.exists()}  ({hadoop_dll})")
print("=" * 55)

spark.stop()