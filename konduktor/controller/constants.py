KONDUKTOR_CONTROLLER_VERSION = "0.1.0"

HARDWARE_XID_ERRORS = (
    48,
    *range(56, 59),
    *range(62, 65),
    *range(68, 78),
    *range(79, 87),
    *range(88, 90),
    92,
    *range(94, 106),
    *range(110, 121),
    *range(122, 126),
)

# The set of all SXid error ids that are known to be harmless.
# See D.4 of https://docs.nvidia.com/datacenter/tesla/pdf/fabric-manager-user-guide.pdf
WHITELISTED_NVSWITCH_SXID_ERRORS = [
    11012,
    11021,
    11022,
    11023,
    12021,
    12023,
    15008,
    15011,
    19049,
    19055,
    19057,
    19059,
    19062,
    19065,
    19068,
    19071,
    24001,
    24002,
    24003,
    22013,
]
