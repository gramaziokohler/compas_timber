"""This is the ONLY component that should have this r: specifier! to prevent rhino from forever re-installing everything."""

# r: compas_timber==1.0.5
import compas

import compas_timber

print(f"compas: {compas.__version__}")
print(f"compas_timber: {compas_timber.__version__}")
