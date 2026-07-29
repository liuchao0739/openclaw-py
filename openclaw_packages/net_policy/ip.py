import re
import ipaddress
import struct
from typing import Optional, Union, List, Tuple, TypedDict


_IPV4_PART = r"(0?\d+|0x[a-f0-9]+)"
_IPV4_REGEXES = {
    "fourOctet": re.compile(r"^" + _IPV4_PART + r"\." + _IPV4_PART + r"\." + _IPV4_PART + r"\." + _IPV4_PART + r"$", re.IGNORECASE),
    "threeOctet": re.compile(r"^" + _IPV4_PART + r"\." + _IPV4_PART + r"\." + _IPV4_PART + r"$", re.IGNORECASE),
    "twoOctet": re.compile(r"^" + _IPV4_PART + r"\." + _IPV4_PART + r"$", re.IGNORECASE),
    "longValue": re.compile(r"^" + _IPV4_PART + r"$", re.IGNORECASE),
}
_OCTAL_RE = re.compile(r"^0[0-7]+$", re.IGNORECASE)
_HEX_RE = re.compile(r"^0x[a-f0-9]+$", re.IGNORECASE)
_FOUR_PART_DECIMAL_RE = re.compile(r"^(0|[1-9]\d*)(\.(0|[1-9]\d*)){3}$")

_ZONE_INDEX = r"%[0-9a-z]{1,}"
_IPV6_PART = r"(?:[0-9a-f]+::?)+"
_IPV6_REGEXES = {
    "zoneIndex": re.compile(_ZONE_INDEX, re.IGNORECASE),
    "native": re.compile(r"^(::)?(" + _IPV6_PART + r")?([0-9a-f]+)?(::)?(" + _ZONE_INDEX + r")?$", re.IGNORECASE),
    "deprecatedTransitional": re.compile(r"^(?:::)(" + _IPV4_PART + r"\." + _IPV4_PART + r"\." + _IPV4_PART + r"\." + _IPV4_PART + r"(" + _ZONE_INDEX + r")?)$", re.IGNORECASE),
    "transitional": re.compile(r"^((?:" + _IPV6_PART + r")|(?:::)(?:" + _IPV6_PART + r")?)" + _IPV4_PART + r"\." + _IPV4_PART + r"\." + _IPV4_PART + r"\." + _IPV4_PART + r"(" + _ZONE_INDEX + r")?$", re.IGNORECASE),
}


def _parse_int_auto(s):
    if _HEX_RE.match(s):
        return int(s, 16)
    if len(s) > 1 and s[0] == "0" and s[1].isdigit():
        if _OCTAL_RE.match(s):
            return int(s, 8)
        raise ValueError(f"ipaddr: cannot parse {s} as octal")
    return int(s, 10)


def _parse_int_js(s):
    if s.lower().startswith("0x"):
        return int(s, 16)
    return int(s, 10)


def _match_cidr(first, second, part_size, cidr_bits):
    if len(first) != len(second):
        raise ValueError("ipaddr: cannot match CIDR for objects with different lengths")
    part = 0
    while cidr_bits > 0:
        shift = part_size - cidr_bits
        if shift < 0:
            shift = 0
        if (first[part] >> shift) != (second[part] >> shift):
            return False
        cidr_bits -= part_size
        part += 1
    return True


def _expand_ipv6(string, num_parts):
    if string.find("::") != string.rfind("::"):
        return None

    colon_count = 0
    last_colon = -1

    zone_id_match = _IPV6_REGEXES["zoneIndex"].search(string)
    zone_id = None
    if zone_id_match:
        zone_id = zone_id_match.group()[1:]
        string = re.sub(r"%.+$", "", string)

    while True:
        last_colon = string.find(":", last_colon + 1)
        if last_colon < 0:
            break
        colon_count += 1

    if string[:2] == "::":
        colon_count -= 1
    if string[-2:] == "::":
        colon_count -= 1

    if colon_count > num_parts:
        return None

    replacement_count = num_parts - colon_count
    replacement = ":"
    for _ in range(replacement_count):
        replacement += "0:"

    string = string.replace("::", replacement, 1)

    if string and string[0] == ":":
        string = string[1:]
    if string and string[-1] == ":":
        string = string[:-1]

    parts = [int(p, 16) for p in string.split(":")]

    return {"parts": parts, "zoneId": zone_id}


class IPv4:
    def __init__(self, octets):
        if len(octets) != 4:
            raise ValueError("ipaddr: ipv4 octet count should be 4")
        for octet in octets:
            if not (0 <= octet <= 255):
                raise ValueError("ipaddr: ipv4 octet should fit in 8 bits")
        self._octets = list(octets)

    @property
    def octets(self):
        return self._octets

    def kind(self):
        return "ipv4"

    def range(self):
        for name, subnets in self._SPECIAL_RANGES:
            for subnet_addr, prefix in subnets:
                if self.match(subnet_addr, prefix):
                    return name
        return "unicast"

    def match(self, other, cidr_range=None):
        if cidr_range is None:
            if isinstance(other, (list, tuple)):
                other, cidr_range = other[0], other[1]
            else:
                raise ValueError("ipaddr: cidr_range is required")
        if other.kind() != "ipv4":
            raise ValueError("ipaddr: cannot match ipv4 address with non-ipv4 one")
        return _match_cidr(self._octets, other._octets, 8, cidr_range)

    def toString(self):
        return ".".join(str(o) for o in self._octets)

    def __str__(self):
        return self.toString()

    def __repr__(self):
        return f"IPv4('{self.toString()}')"

    def __eq__(self, other):
        if isinstance(other, IPv4):
            return self._octets == other._octets
        return NotImplemented

    def __hash__(self):
        return hash(tuple(self._octets))

    @classmethod
    def _parser(cls, string):
        match = _IPV4_REGEXES["fourOctet"].match(string)
        if match:
            return [_parse_int_auto(g) for g in match.groups()]

        match = _IPV4_REGEXES["longValue"].match(string)
        if match:
            value = _parse_int_auto(match.group(1))
            if value > 0xFFFFFFFF or value < 0:
                raise ValueError("ipaddr: address outside defined range")
            result = [(value >> shift) & 0xFF for shift in range(0, 25, 8)]
            result.reverse()
            return result

        match = _IPV4_REGEXES["twoOctet"].match(string)
        if match:
            groups = match.groups()
            value = _parse_int_auto(groups[1])
            if value > 0xFFFFFF or value < 0:
                raise ValueError("ipaddr: address outside defined range")
            return [_parse_int_auto(groups[0]), (value >> 16) & 0xFF, (value >> 8) & 0xFF, value & 0xFF]

        match = _IPV4_REGEXES["threeOctet"].match(string)
        if match:
            groups = match.groups()
            value = _parse_int_auto(groups[2])
            if value > 0xFFFF or value < 0:
                raise ValueError("ipaddr: address outside defined range")
            return [_parse_int_auto(groups[0]), _parse_int_auto(groups[1]), (value >> 8) & 0xFF, value & 0xFF]

        return None

    @classmethod
    def is_valid(cls, string):
        try:
            parts = cls._parser(string)
            if parts is None:
                return False
            cls(parts)
            return True
        except Exception:
            return False

    @classmethod
    def is_valid_four_part_decimal(cls, string):
        return cls.is_valid(string) and _FOUR_PART_DECIMAL_RE.match(string) is not None

    @classmethod
    def parse(cls, string):
        parts = cls._parser(string)
        if parts is None:
            raise ValueError("ipaddr: string is not formatted like an IPv4 Address")
        return cls(parts)

    @classmethod
    def parse_cidr(cls, string):
        match = re.match(r"^(.+)/(\d+)$", string)
        if match:
            mask_length = int(match.group(2))
            if 0 <= mask_length <= 32:
                return (cls.parse(match.group(1)), mask_length)
        raise ValueError("ipaddr: string is not formatted like an IPv4 CIDR range")


IPv4._SPECIAL_RANGES = [
    ("unspecified", [(IPv4([0, 0, 0, 0]), 8)]),
    ("broadcast", [(IPv4([255, 255, 255, 255]), 32)]),
    ("multicast", [(IPv4([224, 0, 0, 0]), 4)]),
    ("linkLocal", [(IPv4([169, 254, 0, 0]), 16)]),
    ("loopback", [(IPv4([127, 0, 0, 0]), 8)]),
    ("carrierGradeNat", [(IPv4([100, 64, 0, 0]), 10)]),
    ("private", [(IPv4([10, 0, 0, 0]), 8), (IPv4([172, 16, 0, 0]), 12), (IPv4([192, 168, 0, 0]), 16)]),
    ("reserved", [(IPv4([192, 0, 0, 0]), 24), (IPv4([192, 0, 2, 0]), 24), (IPv4([192, 88, 99, 0]), 24), (IPv4([198, 18, 0, 0]), 15), (IPv4([198, 51, 100, 0]), 24), (IPv4([203, 0, 113, 0]), 24), (IPv4([240, 0, 0, 0]), 4)]),
    ("as112", [(IPv4([192, 175, 48, 0]), 24), (IPv4([192, 31, 196, 0]), 24)]),
    ("amt", [(IPv4([192, 52, 193, 0]), 24)]),
]


class IPv6:
    def __init__(self, parts, zone_id=None):
        if len(parts) == 16:
            new_parts = []
            for i in range(0, 16, 2):
                new_parts.append((parts[i] << 8) | parts[i + 1])
            parts = new_parts
        elif len(parts) != 8:
            raise ValueError("ipaddr: ipv6 part count should be 8 or 16")

        for part in parts:
            if not (0 <= part <= 0xFFFF):
                raise ValueError("ipaddr: ipv6 part should fit in 16 bits")

        self._parts = list(parts)
        self._zone_id = zone_id

    @property
    def parts(self):
        return self._parts

    def kind(self):
        return "ipv6"

    def range(self):
        for name, subnets in self._SPECIAL_RANGES:
            for subnet_addr, prefix in subnets:
                if self.match(subnet_addr, prefix):
                    return name
        return "unicast"

    def match(self, other, cidr_range=None):
        if cidr_range is None:
            if isinstance(other, (list, tuple)):
                other, cidr_range = other[0], other[1]
            else:
                raise ValueError("ipaddr: cidr_range is required")
        if other.kind() != "ipv6":
            raise ValueError("ipaddr: cannot match ipv6 address with non-ipv6 one")
        return _match_cidr(self._parts, other._parts, 16, cidr_range)

    def isIPv4MappedAddress(self):
        return self.range() == "ipv4Mapped"

    def toIPv4Address(self):
        if not self.isIPv4MappedAddress():
            raise ValueError("ipaddr: trying to convert a generic ipv6 address to ipv4")
        high = self._parts[-2]
        low = self._parts[-1]
        return IPv4([(high >> 8) & 0xFF, high & 0xFF, (low >> 8) & 0xFF, low & 0xFF])

    def toString(self):
        int_val = 0
        for p in self._parts:
            int_val = (int_val << 16) | p
        return str(ipaddress.IPv6Address(int_val))

    def __str__(self):
        return self.toString()

    def __repr__(self):
        return f"IPv6('{self.toString()}')"

    def __eq__(self, other):
        if isinstance(other, IPv6):
            return self._parts == other._parts
        return NotImplemented

    def __hash__(self):
        return hash(tuple(self._parts))

    @classmethod
    def _parser(cls, string):
        match = _IPV6_REGEXES["deprecatedTransitional"].match(string)
        if match:
            return cls._parser(f"::ffff:{match.group(1)}")

        if _IPV6_REGEXES["native"].match(string):
            return _expand_ipv6(string, 8)

        match = _IPV6_REGEXES["transitional"].match(string)
        if match:
            groups = match.groups()
            zone_id = groups[5] or ""
            addr_str = groups[0] or ""
            if not addr_str.endswith("::"):
                addr_str = addr_str[:-1]
            addr = _expand_ipv6(addr_str + zone_id, 6)
            if addr and addr.get("parts"):
                octets = [
                    _parse_int_js(groups[1]),
                    _parse_int_js(groups[2]),
                    _parse_int_js(groups[3]),
                    _parse_int_js(groups[4]),
                ]
                for octet in octets:
                    if not (0 <= octet <= 255):
                        return None
                addr["parts"].append((octets[0] << 8) | octets[1])
                addr["parts"].append((octets[2] << 8) | octets[3])
                return {"parts": addr["parts"], "zoneId": addr.get("zoneId")}

        return None

    @classmethod
    def is_valid(cls, string):
        if not isinstance(string, str) or ":" not in string:
            return False
        try:
            result = cls._parser(string)
            if result is None:
                return False
            cls(result["parts"], result.get("zoneId"))
            return True
        except Exception:
            return False

    @classmethod
    def parse(cls, string):
        result = cls._parser(string)
        if result is None:
            raise ValueError("ipaddr: string is not formatted like an IPv6 Address")
        return cls(result["parts"], result.get("zoneId"))

    @classmethod
    def parse_cidr(cls, string):
        match = re.match(r"^(.+)/(\d+)$", string)
        if match:
            mask_length = int(match.group(2))
            if 0 <= mask_length <= 128:
                return (cls.parse(match.group(1)), mask_length)
        raise ValueError("ipaddr: string is not formatted like an IPv6 CIDR range")


IPv6._SPECIAL_RANGES = [
    ("unspecified", [(IPv6([0, 0, 0, 0, 0, 0, 0, 0]), 128)]),
    ("linkLocal", [(IPv6([0xFE80, 0, 0, 0, 0, 0, 0, 0]), 10)]),
    ("multicast", [(IPv6([0xFF00, 0, 0, 0, 0, 0, 0, 0]), 8)]),
    ("loopback", [(IPv6([0, 0, 0, 0, 0, 0, 0, 1]), 128)]),
    ("uniqueLocal", [(IPv6([0xFC00, 0, 0, 0, 0, 0, 0, 0]), 7)]),
    ("ipv4Mapped", [(IPv6([0, 0, 0, 0, 0, 0xFFFF, 0, 0]), 96)]),
    ("deprecatedSiteLocal", [(IPv6([0xFEC0, 0, 0, 0, 0, 0, 0, 0]), 10)]),
    ("discard", [(IPv6([0x0100, 0, 0, 0, 0, 0, 0, 0]), 64)]),
    ("rfc6145", [(IPv6([0, 0, 0, 0, 0xFFFF, 0, 0, 0]), 96)]),
    ("rfc6052", [(IPv6([0x64, 0xFF9B, 0, 0, 0, 0, 0, 0]), 96), (IPv6([0x64, 0xFF9B, 0x1, 0, 0, 0, 0, 0]), 48)]),
    ("6to4", [(IPv6([0x2002, 0, 0, 0, 0, 0, 0, 0]), 16)]),
    ("teredo", [(IPv6([0x2001, 0, 0, 0, 0, 0, 0, 0]), 32)]),
    ("benchmarking", [(IPv6([0x2001, 0x2, 0, 0, 0, 0, 0, 0]), 48)]),
    ("amt", [(IPv6([0x2001, 0x3, 0, 0, 0, 0, 0, 0]), 32)]),
    ("as112v6", [(IPv6([0x2001, 0x4, 0x112, 0, 0, 0, 0, 0]), 48), (IPv6([0x2620, 0x4F, 0x8000, 0, 0, 0, 0, 0]), 48)]),
    ("deprecatedOrchid", [(IPv6([0x2001, 0x10, 0, 0, 0, 0, 0, 0]), 28)]),
    ("orchid2", [(IPv6([0x2001, 0x20, 0, 0, 0, 0, 0, 0]), 28)]),
    ("droneRemoteIdProtocolEntityTags", [(IPv6([0x2001, 0x30, 0, 0, 0, 0, 0, 0]), 28)]),
    ("segmentRouting", [(IPv6([0x5F00, 0, 0, 0, 0, 0, 0, 0]), 16)]),
    ("reserved", [(IPv6([0x2001, 0, 0, 0, 0, 0, 0, 0]), 23), (IPv6([0x2001, 0xDB8, 0, 0, 0, 0, 0, 0]), 32), (IPv6([0x3FFF, 0, 0, 0, 0, 0, 0, 0]), 20)]),
]


ParsedIpAddress = Union[IPv4, IPv6]


class Ipv4SpecialUseBlockOptions(TypedDict, total=False):
    allowRfc2544BenchmarkRange: bool


class Ipv6SpecialUseBlockOptions(TypedDict, total=False):
    allowUniqueLocalRange: bool


BLOCKED_IPV4_SPECIAL_USE_RANGES = {
    "unspecified",
    "broadcast",
    "multicast",
    "linkLocal",
    "loopback",
    "carrierGradeNat",
    "private",
    "reserved",
}

PRIVATE_OR_LOOPBACK_IPV4_RANGES = {
    "loopback",
    "private",
    "linkLocal",
    "carrierGradeNat",
}

BLOCKED_IPV6_SPECIAL_USE_RANGES = {
    "unspecified",
    "loopback",
    "linkLocal",
    "uniqueLocal",
    "multicast",
    "reserved",
    "benchmarking",
    "discard",
    "orchid2",
}

RFC2544_BENCHMARK_PREFIX = (IPv4.parse("198.18.0.0"), 15)
CLOUD_METADATA_IP_ADDRESSES = {"100.100.100.200", "fd00:ec2::254"}

_EMBEDDED_IPV4_SENTINEL_RULES = [
    {
        "matches": lambda p: p[0] == 0 and p[1] == 0 and p[2] == 0 and p[3] == 0 and p[4] == 0 and p[5] == 0,
        "to_hextets": lambda p: (p[6], p[7]),
    },
    {
        "matches": lambda p: p[0] == 0x0064 and p[1] == 0xFF9B and p[2] == 0x0001 and p[3] == 0 and p[4] == 0 and p[5] == 0,
        "to_hextets": lambda p: (p[6], p[7]),
    },
    {
        "matches": lambda p: p[0] == 0x2002,
        "to_hextets": lambda p: (p[1], p[2]),
    },
    {
        "matches": lambda p: p[0] == 0x2001 and p[1] == 0x0000,
        "to_hextets": lambda p: (p[6] ^ 0xFFFF, p[7] ^ 0xFFFF),
    },
    {
        "matches": lambda p: (p[4] & 0xFCFF) == 0 and p[5] == 0x5EFE,
        "to_hextets": lambda p: (p[6], p[7]),
    },
]


def is_valid(string):
    return IPv6.is_valid(string) or IPv4.is_valid(string)


def parse(string):
    if IPv6.is_valid(string):
        return IPv6.parse(string)
    elif IPv4.is_valid(string):
        return IPv4.parse(string)
    else:
        raise ValueError("ipaddr: the address has neither IPv6 nor IPv4 format")


def parse_cidr(string):
    try:
        return IPv6.parse_cidr(string)
    except Exception:
        try:
            return IPv4.parse_cidr(string)
        except Exception:
            raise ValueError("ipaddr: the address has neither IPv6 nor IPv4 CIDR format")


def is_ipv4_address(address):
    return address.kind() == "ipv4"


def is_ipv6_address(address):
    return address.kind() == "ipv6"


def _normalize_optional_string(value):
    if not isinstance(value, str):
        return None
    trimmed = value.strip()
    return trimmed or None


def _normalize_lowercase_string_or_empty(value):
    return value.strip().lower() if isinstance(value, str) else ""


def _strip_ipv6_brackets(value):
    if value.startswith("[") and value.endswith("]"):
        return value[1:-1]
    return value


def _is_numeric_ipv4_literal_part(value):
    return bool(re.match(r"^[0-9]+$", value) or re.match(r"^0x[0-9a-f]+$", value, re.IGNORECASE))


def _parse_ipv6_with_embedded_ipv4(raw):
    if ":" not in raw or "." not in raw:
        return None
    match = re.match(r"^(.*:)([^:%]+(?:\.[^:%]+){3})(%[0-9A-Za-z]+)?$", raw, re.IGNORECASE)
    if not match:
        return None
    prefix = match.group(1)
    embedded_ipv4 = match.group(2)
    zone_suffix = match.group(3) or ""
    if not IPv4.is_valid_four_part_decimal(embedded_ipv4):
        return None
    octets = [int(part) for part in embedded_ipv4.split(".")]
    high = format((octets[0] << 8) | octets[1], "x")
    low = format((octets[2] << 8) | octets[3], "x")
    normalized_ipv6 = f"{prefix}{high}:{low}{zone_suffix}"
    if not IPv6.is_valid(normalized_ipv6):
        return None
    return IPv6.parse(normalized_ipv6)


def _normalize_ipv4_mapped_address(address):
    if not is_ipv6_address(address):
        return address
    if not address.isIPv4MappedAddress():
        return address
    return address.toIPv4Address()


def _normalize_ip_parse_input(raw):
    trimmed = _normalize_optional_string(raw)
    if not trimmed:
        return None
    return _strip_ipv6_brackets(trimmed)


def parse_canonical_ip_address(raw):
    normalized = _normalize_ip_parse_input(raw)
    if not normalized:
        return None
    if IPv4.is_valid(normalized):
        if not IPv4.is_valid_four_part_decimal(normalized):
            return None
        return IPv4.parse(normalized)
    if IPv6.is_valid(normalized):
        return IPv6.parse(normalized)
    return _parse_ipv6_with_embedded_ipv4(normalized)


def parse_loose_ip_address(raw):
    normalized = _normalize_ip_parse_input(raw)
    if not normalized:
        return None
    if is_valid(normalized):
        return parse(normalized)
    return _parse_ipv6_with_embedded_ipv4(normalized)


def normalize_ip_address(raw):
    parsed = parse_canonical_ip_address(raw)
    if not parsed:
        return None
    normalized = _normalize_ipv4_mapped_address(parsed)
    return _normalize_lowercase_string_or_empty(normalized.toString())


def is_canonical_dotted_decimal_ipv4(raw):
    trimmed = _normalize_optional_string(raw)
    if not trimmed:
        return False
    normalized = _strip_ipv6_brackets(trimmed)
    if not normalized:
        return False
    return IPv4.is_valid_four_part_decimal(normalized)


def is_legacy_ipv4_literal(raw):
    trimmed = _normalize_optional_string(raw)
    if not trimmed:
        return False
    normalized = _strip_ipv6_brackets(trimmed)
    if not normalized or ":" in normalized:
        return False
    if is_canonical_dotted_decimal_ipv4(normalized):
        return False
    parts = normalized.split(".")
    if len(parts) == 0 or len(parts) > 4:
        return False
    if any(len(part) == 0 for part in parts):
        return False
    if not all(_is_numeric_ipv4_literal_part(part) for part in parts):
        return False
    return True


def is_loopback_ip_address(raw):
    parsed = parse_canonical_ip_address(raw)
    if not parsed:
        return False
    normalized = _normalize_ipv4_mapped_address(parsed)
    return normalized.range() == "loopback"


def is_link_local_ip_address(raw):
    parsed = parse_loose_ip_address(raw)
    if not parsed:
        return False
    normalized = _normalize_ipv4_mapped_address(parsed)
    if is_ipv4_address(normalized):
        return normalized.range() == "linkLocal"
    embedded_ipv4 = extract_embedded_ipv4_from_ipv6(normalized)
    if embedded_ipv4 is not None and embedded_ipv4.range() == "linkLocal":
        return True
    return normalized.range() == "linkLocal"


def is_cloud_metadata_ip_address(raw):
    parsed = parse_loose_ip_address(raw)
    if not parsed:
        return False
    normalized = _normalize_ipv4_mapped_address(parsed)
    if is_ipv6_address(normalized):
        embedded_ipv4 = extract_embedded_ipv4_from_ipv6(normalized)
        if embedded_ipv4 is not None and embedded_ipv4.toString() in CLOUD_METADATA_IP_ADDRESSES:
            return True
    return normalized.toString() in CLOUD_METADATA_IP_ADDRESSES


def is_private_or_loopback_ip_address(raw):
    parsed = parse_canonical_ip_address(raw)
    if not parsed:
        return False
    normalized = _normalize_ipv4_mapped_address(parsed)
    if is_ipv4_address(normalized):
        return normalized.range() in PRIVATE_OR_LOOPBACK_IPV4_RANGES
    return is_blocked_special_use_ipv6_address(normalized)


def is_blocked_special_use_ipv6_address(address, options=None):
    range_name = address.range()
    if range_name == "uniqueLocal" and options is not None and options.get("allowUniqueLocalRange") is True:
        return False
    if range_name in BLOCKED_IPV6_SPECIAL_USE_RANGES:
        return True
    return (address.parts[0] & 0xFFC0) == 0xFEC0


def is_rfc1918_ipv4_address(raw):
    parsed = parse_canonical_ip_address(raw)
    if not parsed or not is_ipv4_address(parsed):
        return False
    return parsed.range() == "private"


def is_carrier_grade_nat_ipv4_address(raw):
    parsed = parse_canonical_ip_address(raw)
    if not parsed or not is_ipv4_address(parsed):
        return False
    return parsed.range() == "carrierGradeNat"


def is_blocked_special_use_ipv4_address(address, options=None):
    in_rfc2544 = address.match(RFC2544_BENCHMARK_PREFIX[0], RFC2544_BENCHMARK_PREFIX[1])
    if in_rfc2544 and options is not None and options.get("allowRfc2544BenchmarkRange") is True:
        return False
    return address.range() in BLOCKED_IPV4_SPECIAL_USE_RANGES or in_rfc2544


def _decode_ipv4_from_hextets(high, low):
    octets = [
        (high >> 8) & 0xFF,
        high & 0xFF,
        (low >> 8) & 0xFF,
        low & 0xFF,
    ]
    return IPv4(octets)


def extract_embedded_ipv4_from_ipv6(address):
    if address.isIPv4MappedAddress():
        return address.toIPv4Address()
    if address.range() == "rfc6145":
        return _decode_ipv4_from_hextets(address.parts[6], address.parts[7])
    if address.range() == "rfc6052":
        return _decode_ipv4_from_hextets(address.parts[6], address.parts[7])
    for rule in _EMBEDDED_IPV4_SENTINEL_RULES:
        if not rule["matches"](address.parts):
            continue
        high, low = rule["to_hextets"](address.parts)
        return _decode_ipv4_from_hextets(high, low)
    return None


def is_ip_in_cidr(ip, cidr):
    normalized_ip = parse_canonical_ip_address(ip)
    if not normalized_ip:
        return False
    candidate = cidr.strip()
    if not candidate:
        return False
    comparable_ip = _normalize_ipv4_mapped_address(normalized_ip)
    if "/" not in candidate:
        exact = parse_canonical_ip_address(candidate)
        if not exact:
            return False
        comparable_exact = _normalize_ipv4_mapped_address(exact)
        return (
            comparable_ip.kind() == comparable_exact.kind()
            and comparable_ip.toString() == comparable_exact.toString()
        )

    try:
        parsed_cidr = parse_cidr(candidate)
    except Exception:
        return False

    base_address, prefix_length = parsed_cidr
    comparable_base = _normalize_ipv4_mapped_address(base_address)
    if comparable_ip.kind() != comparable_base.kind():
        return False
    try:
        if is_ipv4_address(comparable_ip) and is_ipv4_address(comparable_base):
            return comparable_ip.match(comparable_base, prefix_length)
        if is_ipv6_address(comparable_ip) and is_ipv6_address(comparable_base):
            return comparable_ip.match(comparable_base, prefix_length)
        return False
    except Exception:
        return False
