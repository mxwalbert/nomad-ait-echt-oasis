# ait-echt-oasis

A NOMAD plugin containing schemas, parsers, etc. for material processing and analysis methods at the ECHT group of AIT.

This `nomad` plugin was generated with `Cookiecutter` along with `@nomad`'s [`cookiecutter-nomad-plugin`](https://github.com/FAIRmat-NFDI/cookiecutter-nomad-plugin) template.

## Development

We use [uv](https://astral.sh) to manage our development environment, dependencies, and tools. Ensure you have `uv` installed on your system before proceeding:

```sh
pip install uv
```

To set up your local development environment, clone the project and navigate into the plugin folder:
```sh
git clone https://github.com/mxwalbert/ait-echt-oasis.git
cd ait-echt-oasis
```

You do **not** need to manually create or activate a virtual environment. `uv run` will automatically manage a virtual environment in the background and ensure all dependencies are perfectly synced.

To load the environment with the dev dependencies you can use:
```sh
uv sync --extra dev
```

### Pre-commit hooks

To ensure that all commits are fully compliant with our formatting, linting, testing, and versioning rules, we use a mandatory pre-commit pipeline. 

Install the pre-commit hooks into your Git configuration:
```sh
uv run pre-commit install
```
This will automatically run Ruff (linting and formatting), Pytest, and verify that the plugin version in `pyproject.toml` is bumped relative to the `main` branch before any commit can be created.

### Run linting and auto-formatting

We use [Ruff](https://docs.astral.sh/ruff/) for linting and formatting the code. You can run Ruff directly through `uv` without manual installation steps:
```sh
uv run ruff check .
uv run ruff format . --check
```

### Run the tests

You can run the tests locally. `uv` will automatically ensure your package is installed in editable mode alongside all `dev` dependencies:
```sh
uv run pytest -sv tests
```

where the `-s` and `-v` options toggle the output verbosity.

Our CI/CD pipeline produces a more comprehensive test report using the `pytest-cov` package. You can generate a local coverage report by injecting it into the runtime environment:
```sh
uv run --with pytest-cov pytest --cov=src tests
```

### Debugging

For interactive debugging of the tests, use `pytest` with the `--pdb` flag:
```sh
uv run pytest -sv --pdb tests
```

We recommend using an IDE for debugging, e.g., _VSCode_. If that is the case, add the following snippet to your `.vscode/launch.json` to make sure it points to the `uv` managed virtual environment:
```json
{
  "configurations": [
      {
        "name": "Debug Pytest via uv",
        "type": "debugpy",
        "request": "launch",
        "cwd": "\${workspaceFolder}",
        "program": "\${workspaceFolder}/.venv/bin/pytest",
        "justMyCode": true,
        "env": {
            "_PYTEST_RAISE": "1"
        },
        "args": [
            "-sv",
            "--pdb",
            "<path-to-plugin-tests>"
        ]
    }
  ]
}
```

where `<path-to-plugin-tests>` must be changed to the local path to the test module to be debugged.

The settings configuration file `.vscode/settings.json` automatically applies the linting and formatting upon saving the modified file.

### Documentation on Github pages

To view the documentation locally, use `uv run` to install and serve `mkdocs` from the definitions file:
```sh
uv run --with-requirements requirements_docs.txt mkdocs serve
```

## Adding this plugin to NOMAD

Currently, NOMAD has two distinct flavors that are relevant depending on your role as an user:
1. [A NOMAD Oasis](#adding-this-plugin-in-your-nomad-oasis): any user with a NOMAD Oasis instance.
2. [Local NOMAD installation and the source code of NOMAD](#adding-this-plugin-in-your-local-nomad-installation-and-the-source-code-of-nomad): internal developers.

### Adding this plugin in your NOMAD Oasis

Read the [NOMAD plugin documentation](https://nomad-lab.eu/prod/v1/staging/docs/howto/oasis/plugins_install.html) for all details on how to deploy the plugin on your NOMAD instance.

### Adding this plugin in your local NOMAD installation and the source code of NOMAD

We now recommend using the dedicated [`nomad-distro-dev`](https://github.com/FAIRmat-NFDI/nomad-distro-dev) repository to simplify the process. Please refer to that repository for detailed instructions.

### Template update

We use [`cruft`](https://github.com/cruft/cruft) to update the project based on template changes. To run the check for updates locally, run:
```sh
uv run cruft update
```
More details see the instructions on [`cruft` website](https://cruft.github.io/cruft/#updating-a-project).

## Main contributors

| Name | E-mail     |
|------|------------|
| Maximilian Wolf | [maximilian.wolf@ait.ac.at](mailto:maximilian.wolf@ait.ac.at) |
