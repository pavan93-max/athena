import shutil, os

db_path = "./chroma_db"
if os.path.exists(db_path):
    shutil.rmtree(db_path)
    print("ChromaDB reset: deleted old database.")
else:
    print("No ChromaDB found, nothing to reset.")
