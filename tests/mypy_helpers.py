import os
import re
import shutil
import sys
from collections import defaultdict
from tempfile import TemporaryDirectory
from textwrap import dedent
from typing import Callable
from typing import Dict
from typing import Iterable
from typing import List
from typing import Tuple

import mypy.api

ERROR_COMMENT_RE = re.compile(r"(\s+# ([NWE]): .*)?$")


def _run_mypy(program: str, *, use_pdb: bool) -> Iterable[str]:
    with TemporaryDirectory() as tempdirname:
        with open(f"{tempdirname}/__main__.py", "w") as f:
            f.write(program)
        config_file = tempdirname + "/mypy.ini"
        shutil.copyfile(os.path.dirname(__file__) + "/mypy.ini", config_file)
        error_pattern = re.compile(
            rf"^{re.escape(f.name)}:" r"(?P<line>\d+): (?P<level>note|warning|error): (?P<message>.*)$"
        )
        mypy_args = [
            f.name,
            "--show-traceback",
            "--raise-exceptions",
            "--show-error-codes",
            "--config-file",
            config_file,
        ]
        if use_pdb:
            mypy_args.append("--pdb")
        stdout, stderr, exit_status = mypy.api.run(mypy_args)
        if stderr:
            print(stderr, file=sys.stderr)  # allow "printf debugging" of the plugin

        # Group errors by line
        messages_by_line: Dict[int, List[Tuple[str, str]]] = defaultdict(list)
        for line in stdout.split("\n"):
            m = error_pattern.match(line)
            if m:
                messages_by_line[int(m.group("line"))].append((m.group("level"), m.group("message")))
            elif line:
                # print(line)  # allow "printf debugging"
                pass

        # Reconstruct the "actual" program with "error" comments
        num_extra_lines = 0
        for line_no, line in enumerate(program.split("\n"), start=1):
            line = ERROR_COMMENT_RE.sub("", line)
            if num_extra_lines > 0:
                if not line.strip():
                    num_extra_lines -= 1
                    continue
                else:
                    num_extra_lines = 0

            messages = messages_by_line.get(line_no)
            if messages:
                for idx, (level, message) in enumerate(messages):
                    cmt = f"{level[0].upper()}: {message}"
                    if idx == 0:
                        yield f"{line}  # {cmt}"
                    else:
                        yield f'{" " * len(line)}  # {cmt}'
                        num_extra_lines += 1
            else:
                yield line


def assert_mypy_output(program: str, *, use_pdb: bool = False) -> None:
    expected = dedent(program).strip()
    actual = "\n".join(_run_mypy(expected, use_pdb=use_pdb))
    assert actual == expected


MypyAssert = Callable[[str], None]
