import os

import kubernetes
import urllib3

from konduktor import logging as konduktor_logging

logger = konduktor_logging.get_logger(__name__)

# Timeout to use for API calls
API_TIMEOUT = 5

_configured = False
_core_api = None


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
        logger.warning("incluster config failed to load, attempting to use kubeconfig.")
        kubernetes.config.load_kube_config()
        logger.info("KUBECONFIG loaded")
    _configured = True


def core_api():
    global _core_api
    if _core_api is None:
        _load_config()
        _core_api = kubernetes.client.CoreV1Api()
    return _core_api


def api_exception():
    return kubernetes.client.rest.ApiException


def config_exception():
    return kubernetes.config.config_exception.ConfigException


def max_retry_error():
    return urllib3.exceptions.MaxRetryError


def stream():
    return kubernetes.stream.stream
