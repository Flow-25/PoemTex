# Contributing

PoemTeX currently has no runtime Python dependencies. Keep the parser explicit,
the generated TeX private, and error messages meaningful to writers rather than
TeX experts.

Run the fast suite:

```sh
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

The equivalent shortcuts are `make test`, `make test-pdf`, `make example`,
`make gallery`, and `make doctor`.

Run the real PDF smoke test:

```sh
PYTHONPATH=src python3 -m poemtex.cli build examples/swiatlo-i-cisza/book.poem
pdfinfo examples/swiatlo-i-cisza/build/swiatlo-i-cisza.pdf
pdftotext examples/swiatlo-i-cisza/build/swiatlo-i-cisza.pdf -
```

Tests should compare parsed structures or normalized generated TeX, not PDF
bytes: PDF timestamps and embedded font details vary across TeX versions.
