from typing import Annotated

from pydantic import StringConstraints

# WKNs are exactly 6 characters; the letters I and O are excluded to avoid
# confusion with digits 1 and 0.
WKN = Annotated[str, StringConstraints(pattern=r"^[A-HJ-NP-Z0-9]{6}$")]

# ISINs are 2 uppercase country-code letters followed by 10 alphanumeric characters.
ISIN = Annotated[str, StringConstraints(pattern=r"^[A-Z]{2}[A-Z0-9]{10}$")]
