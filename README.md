# CSV Cleaner

A simple Python tool for cleaning and validating CSV files.

## Features

- Removes duplicate rows
- Trims unnecessary whitespace
- Detects missing email addresses
- Detects basic invalid email formats
- Validates CSV structure
- Rejects empty or malformed CSV files
- Preserves the original file
- Generates a cleaned output file automatically
- Includes command-line help

## Requirements

- Python 3

No external libraries are required.

## Usage

Run:

```bash
python cleaner.py archivo.csv
```

Example:

```bash
python cleaner.py examples/sample.csv
```

The cleaned file will be created automatically:

```text
examples/sample_limpios.csv
```

## Example output

```text
⚠ Email faltante en fila 4

Resumen:
Filas recibidas:        4
Duplicados eliminados:  1
Emails faltantes:       1
Emails inválidos:       0
Filas exportadas:       3
```

## Help

```bash
python cleaner.py --help
```

## Example files

The `examples/` folder contains:

```text
sample.csv
sample_limpios.csv
```

These files demonstrate the input and output of the cleaner.

## Notes

The program performs basic email validation.

It reports invalid or missing email addresses but does not remove those rows automatically.

## Project structure

```text
csv-cleaner/
├── cleaner.py
├── README.md
├── .gitignore
└── examples/
    ├── sample.csv
    └── sample_limpios.csv
```
