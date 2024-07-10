#!/usr/bin/env bash
set -eo pipefail

# this stops git rev-parse from failing if we run this from the .git directory
builtin cd "$(dirname "${BASH_SOURCE:-$0}")"
ROOT="$(git rev-parse --show-toplevel)"
builtin cd "$ROOT" || exit 1

YAPF_VERSION=$(yapf --version | awk '{print $2}')
RUFF_VERSION=$(ruff --version | head -n 1 | awk '{print $2}')
MYPY_VERSION=$(mypy --version | awk '{print $2}')
BLACK_VERSION=$(black --version | head -n 1 | awk '{print $2}')

echo "ruff ver $YAPF_VERSION"
echo "yapf ver $RUFF_VERSION"
echo "mypy ver $MYPY_VERSION"
echo "black ver $BLACK_VERSION"

YAPF_FLAGS=(
    '--recursive'
    '--parallel'
)

YAPF_EXCLUDES=(
    '--exclude' 'build/**'
)

ISORT_YAPF_EXCLUDES=(
    '--sg' 'build/**'
)

BLACK_INCLUDES=(
    'konduktor'
    'tests'
)

# Format specified files
format() {
    yapf --in-place "${YAPF_FLAGS[@]}" "$@"
}

# Format files that differ from main branch. Ignores dirs that are not slated
# for autoformat yet.
format_changed() {
    # The `if` guard ensures that the list of filenames is not empty, which
    # could cause yapf to receive 0 positional arguments, making it hang
    # waiting for STDIN.
    #
    # `diff-filter=ACM` and $MERGEBASE is to ensure we only format files that
    # exist on both branches.
    MERGEBASE="$(git merge-base origin/main HEAD)"

    if ! git diff --diff-filter=ACM --quiet --exit-code "$MERGEBASE" -- '*.py' '*.pyi' &>/dev/null; then
        git diff --name-only --diff-filter=ACM "$MERGEBASE" -- '*.py' '*.pyi' | xargs -P 5 \
             yapf --in-place "${YAPF_EXCLUDES[@]}" "${YAPF_FLAGS[@]}"
    fi

}

# Format all files
format_all() {
    yapf --in-place "${YAPF_FLAGS[@]}" "${YAPF_EXCLUDES[@]}" konduktor tests
}

echo 'Konduktor Black:'
black "${BLACK_INCLUDES[@]}"

## This flag formats individual files. --files *must* be the first command line
## arg to use this option.
if [[ "$1" == '--files' ]]; then
   format "${@:2}"
   # If `--all` is passed, then any further arguments are ignored and the
   # entire python directory is formatted.
elif [[ "$1" == '--all' ]]; then
   format_all
else
   # Format only the files that changed in last commit.
   format_changed
fi
echo 'Konduktor yapf: Done'

echo 'Konduktor isort:'
isort konduktor tests "${ISORT_YAPF_EXCLUDES[@]}"


# Run mypy
echo 'Konduktor mypy:'
mypy $(cat tests/mypy_files.txt)

# Run Pylint
echo 'Konduktor Pylint:'
ruff check konduktor tests
