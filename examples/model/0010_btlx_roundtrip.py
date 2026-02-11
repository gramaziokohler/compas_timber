"""
Script to read a BTLx file and write it back with a suffix.
Used for testing BTLx read/write roundtrip functionality.
"""

import argparse
import os

from compas.tolerance import Tolerance

from compas_timber.btlx import BTLxReader
from compas_timber.fabrication import BTLxWriter


def main(filepath, suffix="_roundtrip"):
    """Read a BTLx file and write it back with a suffix.

    Parameters
    ----------
    filepath : str
        Path to the BTLx file to read.
    suffix : str, optional
        Suffix to add to the output filename. Defaults to "_roundtrip".
    """
    # Validate input file exists
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"BTLx file not found: {filepath}")

    print(f"Reading BTLx file: {filepath}")

    # Read the BTLx file
    reader = BTLxReader(Tolerance(unit="MM", precision=3))
    print(f"Reader unit: {reader._unit}, precision: {reader._precision}")
    model = reader.read(filepath)
    print(f"Reader unit after read: {reader._unit}, precision: {reader._precision}")
    print(f"Model tolerance: {model.tolerance}")

    # Report any errors
    if reader.errors:
        print(f"Reader encountered {len(reader.errors)} errors:")
        for error in reader.errors:
            print(f"  - {error}")

    print(f"Successfully read model with {len(list(model.elements()))} elements")

    # Generate output filepath
    base_dir = os.path.dirname(filepath)
    base_name = os.path.splitext(os.path.basename(filepath))[0]
    output_filepath = os.path.join(base_dir, f"{base_name}{suffix}.btlx")

    print(f"Writing BTLx file: {output_filepath}")

    # Write the model back to BTLx
    writer = BTLxWriter()
    writer.write(model, output_filepath)
    print(writer._tolerance, "tolerance in writer")

    print("Done!")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Read and rewrite a BTLx file with a suffix")
    parser.add_argument("filepath", help="Path to the BTLx file")
    parser.add_argument("--suffix", default="_roundtrip", help="Suffix for output file (default: _roundtrip)")

    args = parser.parse_args()
    main(args.filepath, args.suffix)
