import sys

from . import EXTRACTORES
from .sri_ventas import registrar_fuente


def main():
    registrar_fuente()
    argumentos = [a for a in sys.argv[1:] if not a.startswith("--")]
    forzar = "--forzar" in sys.argv
    if not argumentos and "--todos" not in sys.argv:
        print("Extractores disponibles:", ", ".join(EXTRACTORES) or "(ninguno todavía)")
        return
    nombres = list(EXTRACTORES) if "--todos" in sys.argv else argumentos
    for nombre in nombres:
        if nombre not in EXTRACTORES:
            print(f"{nombre}: no existe")
            continue
        r = EXTRACTORES[nombre]().ejecutar(forzar=forzar)
        print(f"{nombre}: {r['estado']} · nuevos {r['nuevos']} · actualizados {r['actualizados']} · {r['mensaje'] or ''}")


if __name__ == "__main__":
    main()
