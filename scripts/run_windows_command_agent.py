"""Run the fixed-operation Riverview command agent on DESKTOP-JA3RPNQ.

File Revision: 1.0.0
Component: COMMS5-WINDOWS-COMMAND-GATEWAY
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from riverview_core.comms5.command_gateway import main


if __name__ == "__main__":
    main()
