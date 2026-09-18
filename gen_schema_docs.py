import importlib
import inspect
import os
import sys

import mkdocs_gen_files

# Ensure the src directory is in the Python path so we can import the package
sys.path.insert(0, os.path.abspath('src'))

SCHEMA_PACKAGES = [
    'nomad_ait_echt_oasis.schema_packages.infrastructure.v0',
    'nomad_ait_echt_oasis.schema_packages.physical_vapor_deposition.v0',
    'nomad_ait_echt_oasis.schema_packages.sputter_deposition.v0',
    'nomad_ait_echt_oasis.schema_packages.vapor_deposition.v0',
]

for package_name in SCHEMA_PACKAGES:
    try:
        mod = importlib.import_module(package_name)
    except Exception as e:
        print(f'Warning: Could not import {package_name}: {e}', file=sys.stderr)
        continue

    # Find classes defined in this module
    classes = []
    for name, obj in inspect.getmembers(mod, inspect.isclass):
        if obj.__module__ == package_name:
            classes.append(obj)

    if not classes:
        continue

    # Create a markdown file for this package
    pkg_short = package_name.split('.')[-2]  # e.g. infrastructure
    md_filename = f'reference/schema_{pkg_short}.md'

    with mkdocs_gen_files.open(md_filename, 'w') as f:
        title = pkg_short.replace('_', ' ').title()
        f.write(f'# {title} Schema\n\n')
        f.write('```mermaid\n')
        f.write('classDiagram\n')

        for cls in classes:
            f.write(f'  class {cls.__name__} {{\n')
            # Try to use NOMAD m_def
            if hasattr(cls, 'm_def'):
                for quant in cls.m_def.quantities:
                    # type might be a primitive, a Section, or an Enum
                    type_name = 'str'
                    if hasattr(quant.type, '__name__'):
                        type_name = quant.type.__name__
                    elif hasattr(quant.type, '__class__'):
                        type_name = quant.type.__class__.__name__

                    # Sanitize for mermaid
                    type_name = type_name.replace('<', '').replace('>', '')
                    f.write(f'    +{type_name} {quant.name}\n')
            else:
                # Fallback, just look for Quantity attributes
                for attr_name, attr_val in inspect.getmembers(cls):
                    if type(attr_val).__name__ == 'Quantity':
                        f.write(f'    +Quantity {attr_name}\n')
            f.write('  }\n')

            # Base classes
            for base in cls.__bases__:
                if base.__name__ not in ('object', 'ArchiveSection', 'Section'):
                    f.write(f'  {cls.__name__} --|> {base.__name__}\n')
                    # Add base class to diagram if not defined in the same module
                    if base.__module__ != package_name:
                        # Give it a stereotype to indicate it's external
                        bname = base.__name__
                        bmod = base.__module__
                        f.write(f'  class {bname} {{\n<<from {bmod}>>\n}}\n')

            # SubSections
            if hasattr(cls, 'm_def'):
                for sub in cls.m_def.sub_sections:
                    sub_sec_name = sub.sub_section.name
                    f.write(f'  {cls.__name__} *-- {sub_sec_name} : {sub.name}\n')
                    if sub.sub_section.section_cls.__module__ != package_name:
                        short = sub.sub_section.section_cls.__module__.split('.')[-1]
                        f.write(f'  class {sub_sec_name} {{\n<<from {short}>>\n}}')

        f.write('```\n')
