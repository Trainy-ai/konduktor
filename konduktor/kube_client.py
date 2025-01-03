import functools
import os
from typing import Optional

import kubernetes
import urllib3

from konduktor import logging as konduktor_logging

logger = konduktor_logging.get_logger(__name__)

# Timeout to use for API calls
API_TIMEOUT = 5
DEFAULT_NAMESPACE = 'default'

_configured = False
_core_api = None
_jobset_api = None

# For dashboard
_batch_api = None
_crd_api = None


def _load_config():
    global _configured
    if _configured:
        return
    try:
        os.environ["KUBERNETES_SERVICE_HOST"] = "kubernetes.default.svc"
        os.environ["KUBERNETES_SERVICE_PORT"] = "443"
        kubernetes.config.load_incluster_config()
        logger.info("incluster k8s config loaded")
    except kubernetes.config.config_exception.ConfigException:
        # this should really only be loaded for debugging.
        logger.debug("incluster config failed to load, attempting to use kubeconfig.")
        kubernetes.config.load_kube_config()
        logger.info("KUBECONFIG loaded")
    _configured = True


def core_api():
    global _core_api
    if _core_api is None:
        _load_config()
        _core_api = kubernetes.client.CoreV1Api()
    return _core_api


def batch_api():
    global _batch_api
    if _batch_api is None:
        _load_config()
        _batch_api = kubernetes.client.BatchV1Api()
    return _batch_api


def crd_api():
    global _crd_api
    if _crd_api is None:
        _load_config()
        _crd_api = kubernetes.client.CustomObjectsApi()
    return _crd_api


def api_exception():
    return kubernetes.client.rest.ApiException


def config_exception():
    return kubernetes.config.config_exception.ConfigException


def max_retry_error():
    return urllib3.exceptions.MaxRetryError


def stream():
    return kubernetes.stream.stream


@functools.lru_cache()
def get_kube_config_context_namespace(
        context_name: Optional[str] = None) -> str:
    """Get the current kubernetes context namespace from the kubeconfig file

    Returns:
        str | None: The current kubernetes context namespace if it exists, else
            the default namespace.
    """

    try:
        contexts, current_context = kubernetes.config.list_kube_config_contexts()
        if context_name is None:
            context = current_context
        else:
            context = next((c for c in contexts if c['name'] == context_name),
                           None)
            if context is None:
                return DEFAULT_NAMESPACE

        if 'namespace' in context['context']:
            return context['context']['namespace']
        else:
            return DEFAULT_NAMESPACE
    except kubernetes.config.config_exception.ConfigException:
        return DEFAULT_NAMESPACE


@functools.lru_cache()
def get_current_kube_config_context_name() -> Optional[str]:
    """Get the current kubernetes context from the kubeconfig file

    Returns:
        str | None: The current kubernetes context if it exists, None otherwise
    """
    try:
        _, current_context = kubernetes.config.list_kube_config_contexts()
        return current_context['name']
    except kubernetes.config.config_exception.ConfigException:
        return None
