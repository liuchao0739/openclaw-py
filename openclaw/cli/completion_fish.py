from __future__ import annotations


def generate_fish_completion(program_name: str = "openclaw") -> str:
    return f"""# Fish completion for {program_name}
complete -c {program_name} -f
"""


def install_fish_completion(program_name: str = "openclaw") -> str:
    return generate_fish_completion(program_name)
