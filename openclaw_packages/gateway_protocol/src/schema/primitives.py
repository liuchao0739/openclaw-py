from typing import Literal

INPUT_PROVENANCE_UNTRUSTED: Literal["untrusted"] = "untrusted"
INPUT_PROVENANCE_TRUSTED: Literal["trusted"] = "trusted"
InputProvenance = Literal["untrusted", "trusted"]
