# KonduktorD

KonduktorD is a subcomponent of Konduktor. KonduktorD runs as a daemonset on all GPU nodes within the cluster
and will listen to container/node logs/metrics for GPU or fabric related errors. Upon detecting either a log or
metric that indicates a fault, KonduktorD will taint the node so that no new workloads will be scheduled on this
node. The responsibility of removing the taint doesn't fall on KonduktorD but rather the Konduktor controller
which will monitor nodes containing the taint and a series of lightweight health checks (compute, memorory, nccl)
which if passed will remove the taint placing the node back into the compute pool.