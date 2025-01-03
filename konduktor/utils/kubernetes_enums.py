import enum


class KubernetesAutoscalerType(enum.Enum):
    """Enum for the different types of cluster autoscalers for Kubernetes."""
    GKE = 'gke'
    GENERIC = 'generic'
