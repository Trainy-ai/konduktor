"""Accelerator registry."""

from konduktor.utils import ux_utils

_ACCELERATORS = [
    'A100',
    'A100-80GB',
    'H100',
]

def is_schedulable_non_gpu_accelerator(accelerator_name: str) -> bool:
    """Returns if this accelerator is a 'schedulable' non-GPU accelerator."""
    for name in _SCHEDULABLE_NON_GPU_ACCELERATORS:
        if name in accelerator_name.lower():
            return True
    return False


def canonicalize_accelerator_name(accelerator: str) -> str:
    """Returns the canonical accelerator name."""

    # Common case: do not read the catalog files.
    mapping = {name.lower(): name for name in _ACCELERATORS}
    if accelerator.lower() in mapping:
        return mapping[accelerator.lower()]

    names = list(searched.keys())

    # Exact match.
    if accelerator in names:
        return accelerator

    if len(names) == 1:
        return names[0]

    # Do not print an error message here. Optimizer will handle it.
    if not names:
        return accelerator

    # Currently unreachable.
    # This can happen if catalogs have the same accelerator with
    # different names (e.g., A10g and A10G).
    assert len(names) > 1
    with ux_utils.print_exception_no_traceback():
        raise ValueError(f'Accelerator name {accelerator!r} is ambiguous. '
                         f'Please choose one of {names}.')
