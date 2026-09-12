from pathlib import Path

#LIST OF FOLDERS
folders =[
    "src",
    "documents",
    "templates",
    "static",
    "uploads",
    "data",
]

#List of files
files = [
    #root files
    "app.py",
    "data_ingestion.py",
    "requirements.txt",
    "Dockerfile",
    ".env",

    #source files
    "src/__init__.py", #constuctor file where we will be importig our functionilty
    "src/config.py",
    "src/db.py",
    "src/ingestion.py",
    "src/models.py",
    "src/self_rag.py",
    "src/vectorstore.py",

    #frontend
    "templates/index.html",
    "static/style.css",
    "static/app.js",

]
def create_project_structure():
    #create folders
    for folder in folders:
        Path(folder).mkdir(parents=True,exist_ok =True)

    #Create files
    for file in files:
        Path(file).touch(exist_ok=True)

    print("Project structure created succesfully ")

if __name__ == "__main__":
    create_project_structure()

