"""
Alias di compatibilità: espone il vero pacchetto annidato
`fuel_blending.fuel_blending` con il nome canonico `fuel_blending`.
"""

import importlib, sys, types

_inner = importlib.import_module("fuel_blending.fuel_blending")
# Copia tutti gli attributi del pacchetto interno in quello esterno
globals().update(_inner.__dict__)
sys.modules[__name__] = _inner        # fa funzionare `import fuel_blending.blending`
