cd D:\dev\python\mesh
d:

pip uninstall K3ANO-NewNodes

type nul > K3ANO_NewNodes\__init__.py

python setup.py bdist_wheel

pip install -e D:\dev\python\mesh

