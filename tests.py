import os

files = os.listdir("gkcore/tests")

for file in files:
    if file != "__init__.py":
        os.system("python3 gkcore/tests/" + file)
