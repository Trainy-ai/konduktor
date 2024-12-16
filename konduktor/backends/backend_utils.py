import uuid

from konduktor.utils import common_utils


def generate_cluster_name():
    # TODO: change this ID formatting to something more pleasant.
    # User name is helpful in non-isolated accounts, e.g., GCP, Azure.
    return f'konduktor-{uuid.uuid4().hex[:4]}-{common_utils.get_cleaned_username()}'