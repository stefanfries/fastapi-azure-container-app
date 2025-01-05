def convert_to_int(value: str) -> int:
    # Remove leading and trailing spaces
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
