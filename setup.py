from setuptools import setup, find_packages

setup(
    name='zen',
    version='0.5.1',
    author='Rolf Simoes',
    author_email='rolf.simoes@opengeohub.org',
    description='A Python Library for Interacting with Zenodo',
    packages=find_packages(),
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Intended Audience :: Science/Research'
    ],
    install_requires=open('requirements.txt').readlines()
)
