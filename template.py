import os
from pathlib import Path

project_name = "financial_fraud_analytics"

list_of_files = [

    # ================= ROOT =================

    ".gitignore",
    "requirements.txt",
    "setup.py",
    "template.py",
    "README.md",
    ".env",

    # ================= CONFIG =================

    "config/config.yaml",
    "config/schema.yaml",

    # ================= DATA =================

    "data/raw/.gitkeep",

    "data/processed/bronze/.gitkeep",
    "data/processed/silver/.gitkeep",
    "data/processed/gold/.gitkeep",

    "data/warehouse/.gitkeep",

    # ================= ARTIFACTS =================

    "artifacts/.gitkeep",
    "artifacts/ingestion/.gitkeep",
    "artifacts/transformation/.gitkeep",
    "artifacts/loading/.gitkeep",

    # ================= SQL =================

    "sql/warehouse_setup.sql",
    "sql/aml_queries.sql",

    # ================= REPORTS =================

    "reports/dashboard_wireframe.pdf",
    "reports/powerbi.pbix",

    # ================= LOGS =================

    "logs/.gitkeep",

    # ================= NOTEBOOKS =================

    "notebooks/.gitkeep",

    # ================= DOCS =================

    "docs/.gitkeep",

    # ================= TESTS =================

    "tests/__init__.py",
    "tests/test_schema.py",
    "tests/test_quality.py",

    # ================= SRC =================

    f"src/{project_name}/__init__.py",

    # ---------- components ----------

    f"src/{project_name}/components/__init__.py",
    f"src/{project_name}/components/extraction.py",
    f"src/{project_name}/components/transformation.py",
    f"src/{project_name}/components/loading.py",

    # ---------- config ----------

    f"src/{project_name}/config/__init__.py",
    f"src/{project_name}/config/configuration.py",

    # ---------- constants ----------

    f"src/{project_name}/constants/__init__.py",
    f"src/{project_name}/constants/constants.py",

    # ---------- entity ----------

    f"src/{project_name}/entity/__init__.py",
    f"src/{project_name}/entity/config_entity.py",
    f"src/{project_name}/entity/artifact_entity.py",

    # ---------- exception ----------

    f"src/{project_name}/exception/__init__.py",
    f"src/{project_name}/exception/exception.py",

    # ---------- logger ----------

    f"src/{project_name}/logger/__init__.py",
    f"src/{project_name}/logger/logging.py",

    # ---------- pipelines ----------

    f"src/{project_name}/pipelines/__init__.py",
    f"src/{project_name}/pipelines/training_pipeline.py",
    f"src/{project_name}/pipelines/prediction_pipeline.py",

    # ---------- utils ----------

    f"src/{project_name}/utils/__init__.py",
    f"src/{project_name}/utils/utils.py",
]


for filepath in list_of_files:

    filepath = Path(filepath)

    filedir, filename = os.path.split(filepath)

    if filedir != "":
        os.makedirs(filedir, exist_ok=True)

    if (not os.path.exists(filepath)) or (os.path.getsize(filepath) == 0):
        with open(filepath, "w") as f:
            pass


print("✅ Enterprise Project Structure Created")