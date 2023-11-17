from setuptools import setup, find_packages

setup(
    name='zen',
    version='0.1.0',
    author='Rolf Simoes',
    author_email='rolf.simoes@opengeohub.org',
    description='Zenodo API client and big dataset manangement',
    packages=find_packages(),
    install_requires=open('requirements.txt').readlines()
)
