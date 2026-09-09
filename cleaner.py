import csv
import sys

if "--help" in sys.argv or "-h" in sys.argv:
    print("MARS CSV Cleaner")
    print()
    print("Uso:")
    print("  python cleaner.py archivo.csv")
    print()
    print("Funciones:")
    print("  - Elimina filas duplicadas")
    print("  - Limpia espacios sobrantes")
    print("  - Detecta emails faltantes")
    print("  - Detecta emails inválidos")
    print("  - Valida la estructura del CSV")
    print("  - Conserva intacto el archivo original")
    sys.exit(0)

if len(sys.argv) < 2:
    print("Error: falta indicar un archivo CSV.")
    print("Usá 'python cleaner.py --help' para ver la ayuda.")
    sys.exit(1)

archivo_entrada = sys.argv[1]

if not archivo_entrada.lower().endswith(".csv"):
    print("Error: el archivo debe tener extensión '.csv'")
    sys.exit(1)

archivo_salida = archivo_entrada[:-4] + "_limpios.csv"

filas_unicas = []
filas_vistas = set()
total_filas = 0
duplicados = 0
emails_faltantes = 0
emails_invalidos = 0

try:
    with open(archivo_entrada, newline="", encoding="utf-8") as archivo:
        lector = csv.DictReader(archivo)
        columnas = lector.fieldnames

        if columnas is None:
            print("Error: el CSV está vacío")
            sys.exit(1)

        if "email" not in columnas:
            print("Error: el CSV no contiene una columna 'email'")
            sys.exit(1)

        for fila in lector:            
            total_filas += 1

            if None in fila or None in fila.values():
                print(f"Error: estructura inválida en fila {total_filas}")
                sys.exit(1)

            fila = {clave: valor.strip() for clave, valor in fila.items()}

            if not fila["email"]:
                emails_faltantes += 1
                print(f"⚠ Email faltante en fila {total_filas}")

            elif (
                "@" not in fila["email"]
                or not fila["email"].split("@", 1)[0]
                or "." not in fila["email"].split("@", 1)[1]
            ):
                emails_invalidos += 1
                print(f"⚠ Email inválido en fila {total_filas}: {fila['email']}")

            identificador = tuple(fila.items())

            if identificador not in filas_vistas:
                filas_vistas.add(identificador)
                filas_unicas.append(fila)
            else:
                duplicados += 1

except FileNotFoundError:
    print(f"Error: no existe el archivo '{archivo_entrada}'")
    sys.exit(1)

with open(archivo_salida, "w", newline="", encoding="utf-8") as archivo:
    escritor = csv.DictWriter(archivo, fieldnames=columnas)

    escritor.writeheader()
    escritor.writerows(filas_unicas)

print(f"Archivo limpio creado: {archivo_salida}")
print()
print("MARS CSV Cleaner")
print()
print(f"Filas recibidas:       {total_filas}")
print(f"Duplicados eliminados: {duplicados}")
print(f"Emails faltantes:      {emails_faltantes}")
print(f"Emails inválidos:      {emails_invalidos}")
print(f"Filas exportadas:      {len(filas_unicas)}")
