"""Constants for usage collection."""

import os

KONDUKTOR_DISABLE_USAGE_COLLECTION = os.environ.get(
    'KONDUKTOR_DISABLE_USAGE_COLLECTION',
    False
)

POSTHOG_API_KEY = os.environ.get(
    'POSTHOG_API_KEY', 'phc_4UgX80BfVNmYRZ2o3dJLyRMGkv1CxBozPAcPnD29uP4')

POSTHOG_HOST = os.environ.get('POSTHOG_HOST', 'https://us.i.posthog.com')

USAGE_POLICY_MESSAGE = (
    'Konduktor collects usage data to improve its services. '
    '`run` commands are not collected to '
    'ensure privacy.\n'
    'Usage logging can be disabled by setting the '
    'environment variable KONDUKTOR_DISABLE_USAGE_COLLECTION=1.')
