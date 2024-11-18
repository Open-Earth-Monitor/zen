# Contributing

## Design principles and intended scope

The **zen** aims to provide a user-friendly utility package for managing large datasets on Zenodo.

All contributions to this software should fall within the scope described above, unless discussed beforehand by the core development team.

## Issue reporting and suggestions

For reporting issues and making feature suggestions please refer to the [issue tracker](https://gitlab.opengeohub.org/rolfsimoes/zen/issues) using the existing templates.

## Contributing code and documentation

### Initial setup

1. Clone the repo: `git clone https://gitlab.opengeohub.org/rolfsimoes/zen/zen.git`
2. Install dependencies (not needed if only contributing documentation):
  - for the Python package: `pip install -r requirements.txt` into a Python 3.6+ environment

### Building and Deploying Documentation  

#### Overview of Documentation Files  

The Sphinx documentation is composed of the following key files in the `sphinx/` directory:  
- **`index.rst`**: The main entry point, containing the table of contents and an overview of the documentation structure.  
- **Topic-specific `.rst` files**:  
  - `api.rst`, `dataset.rst`, `metadata.rst`, `modules.rst`, `utils.rst`: These files contain detailed information about specific aspects of the project, such as APIs, datasets, and utility functions.  
- **`conf.py`**: Configuration file for the Sphinx build system, specifying settings like extensions, themes, and project metadata.  
- **Assets (`img/` folder)**: Includes images used in the documentation, such as `zen-logo.png`.  

You can update these files to modify or expand the documentation.  

#### Steps to Build and Deploy Documentation  

1. **Clean and build the documentation**:  
   Go to the project folder and run the following commands to clean and rebuild the Sphinx documentation:  
   ```bash
   make clean
   make html
   ```  
   The generated documentation will be located in the `./sphinx/_build/html` folder.  

2. **Deploy the documentation**:  
   Update the `docs/` folder with the new documentation files:  
   ```bash
   rm -fr docs/*
   cp -r sphinx/_build/html/* docs/
   touch docs/.nojekyll
   ```

4. **Commit and push the changes**:  
   Add the changes and commit using the `docs` type in the commit message format:  
   ```bash
   git add docs  
   git commit -m "docs: update deployed documentation"  
   git push  
   ```  

### Development

All changes to code and documentation should be made in a separate branch, created from an up-to-date local `main`. The **branch name** must refer a open issue (``i{ISSUE_ID}``):

```bash
git checkout main
git pull
git checkout -b i0

git add [CHANGED FILES]
git commit -m "fix(scope): resolves #0; [GENERAL COMMENT]"

git checkout main
git pull
git merge i0
git push

git branch -d i0
```

If you do not have the appropriate permissions to submit new branches to the **zen** repository, you may fork this repository into your own Github namespace and submit merge requests from there.

### Commit conventions

All commit message should be structured as follows:

```
<type>[optional scope]: <description>

[optional body]

[optional footer(s)]

```

**Type**

Must be one of the following:

- **build**: Changes that affect the build system or external dependencies
- **ci**: Changes to our CI configuration files and scripts
- **docs**: Documentation only changes
- **feat**: A new feature
- **fix**: A bug fix
- **perf**: A code change that improves performance
- **refactor**: A code change that neither fixes a bug nor adds a feature
- **style**: Changes that do not affect the meaning of the code (white-space, formatting, missing semi-colons, etc)
- **test**: Adding missing tests or correcting existing tests

Based on [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/).

### Code conventions

We strongly prefer to submit code to **zen** with [type hints](https://docs.python.org/3/library/typing.html). Additionally, we support Python versions as low as 3.8 and no code that uses syntax introduced in later versions of Python (e.g. the walrus operator) will be accepted.

There are currently no style restrictions guidelines imposed upon code contributions. This may change at a later date.

### Versioning

We adthere to standard [semantic versioning](https://semver.org/). Since we release from `main` <!-- needs to be discussed -->
all merge requests should be accompanied with a version increment and the responsibility for increasing the version number falls on the contributor merging a branch: when merging a request either increment the MINOR version and reset the PATCH version to zero (if the intent of the merge request is to add new features) or increment the PATCH version (if the merge request only contains bugfixes). When merging a branch made by another contributor (e.g. because they do not have the required permissions to do so) please confirm the intent of the merge request (i.e. which semver number needs to be incremented).

When incrementing the version of **zen** it is enough to write the version change into [`__init__.py`](./zen/__init__.py) in the appropriate branch.