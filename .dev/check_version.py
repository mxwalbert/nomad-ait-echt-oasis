import re
import subprocess
import sys

try:
    from packaging.version import parse as parse_version
except ImportError:
    print(
        'Error: packaging module not found. Please ensure dependencies are installed.'
    )
    sys.exit(1)


def get_version(content):
    match = re.search(r'^version\s*=\s*["\']([^"\']+)["\']', content, re.MULTILINE)
    if match:
        return match.group(1)
    return None


def main():
    with open('pyproject.toml', encoding='utf-8') as f:
        local_content = f.read()

    local_version_str = get_version(local_content)
    if not local_version_str:
        print('Error: Could not find version in pyproject.toml')
        sys.exit(1)

    local_version = parse_version(local_version_str)

    # try to get version from origin/main, then main
    main_version_str = None
    branch_used = None
    for branch in ['origin/main', 'main']:
        try:
            # check_output will raise CalledProcessError if branch doesn't exist
            main_content = subprocess.check_output(
                ['git', 'show', f'{branch}:pyproject.toml'],
                stderr=subprocess.DEVNULL,
                text=True,
            )
            main_version_str = get_version(main_content)
            if main_version_str:
                branch_used = branch
                break
        except subprocess.CalledProcessError:
            continue

    if not main_version_str:
        print(
            'Warning: Could not fetch pyproject.toml from main or origin/main. '
            + 'Skipping version bump check.'
        )
        sys.exit(0)

    main_version = parse_version(main_version_str)

    if local_version <= main_version:
        print(
            'Error: Version must be bumped! '
            + f'Current version ({local_version_str}) is not '
            + f'greater than {branch_used} version ({main_version_str}).'
        )
        sys.exit(1)
    else:
        print(
            'Version check passed: '
            + f'{local_version_str} > {main_version_str} ({branch_used})'
        )
        sys.exit(0)


if __name__ == '__main__':
    main()
