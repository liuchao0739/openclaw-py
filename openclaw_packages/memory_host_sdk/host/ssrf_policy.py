from __future__ import annotations

from typing import Any, Dict, List, Optional


class SsrFPolicy:
    def __init__(
        self,
        allow_private_network: bool = False,
        dangerously_allow_private_network: bool = False,
        allow_rfc2544_benchmark_range: bool = False,
        allow_ipv6_unique_local_range: bool = False,
        allowed_hostnames: Optional[List[str]] = None,
        hostname_allowlist: Optional[List[str]] = None,
    ):
        self.allow_private_network = allow_private_network
        self.dangerously_allow_private_network = dangerously_allow_private_network
        self.allow_rfc2544_benchmark_range = allow_rfc2544_benchmark_range
        self.allow_ipv6_unique_local_range = allow_ipv6_unique_local_range
        self.allowed_hostnames = allowed_hostnames or []
        self.hostname_allowlist = hostname_allowlist or []

    def to_dict(self) -> Dict[str, Any]:
        return {
            "allowPrivateNetwork": self.allow_private_network,
            "dangerouslyAllowPrivateNetwork": self.dangerously_allow_private_network,
            "allowRfc2544BenchmarkRange": self.allow_rfc2544_benchmark_range,
            "allowIpv6UniqueLocalRange": self.allow_ipv6_unique_local_range,
            "allowedHostnames": self.allowed_hostnames,
            "hostnameAllowlist": self.hostname_allowlist,
        }
