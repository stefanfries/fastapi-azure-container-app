def convert_to_int(value: str) -> int:
    """
    Convert a string representation of a number to an integer.
    This function handles strings with the abbreviation 'Mio' (which stands for million)
    by removing the abbreviation and converting the remaining number to an integer,
    multiplying by 1,000,000. It also handles commas and periods in the string.
    Args:
        value (str): The string representation of the number to convert.
    Returns:
        int: The integer representation of the input string.
    """
    value = value.strip()

    # Handle 'Mio.' and similar abbreviations
    if "Mio" in value:
        # Remove "Mio." and any other spaces
        value = value.replace("Mio", "").strip()

        # Convert the number to an integer, handling commas and periods
        number = float(value.replace(",", "."))

        # Multiply by 1 million (since 'Mio' means million)
        return int(number * 1_000_000)

    # If no 'Mio' is present, just clean the string and convert to integer
    return int(value.replace(",", "").replace(".", ""))
