# Third-party code

Everything in this repository is licensed under the Apache License, Version 2.0 (see `LICENSE`), **except the files below**, which were not written here and keep their own licences.

| File | What it is | Licence |
|---|---|---|
| `prototype/project/support.js` | A minified bundle of React and ReactDOM: the runtime the design-canvas format of the prototype needs. The original `@license` headers are still in the file. | MIT, Copyright (c) Facebook, Inc. and its affiliates. |
| `prototype/project/fonts/*.woff2` | Three font families, Latin subsets, so the prototype looks the same offline and sends no request to a font server: Public Sans (interface), Source Serif 4 (requirement wording) and JetBrains Mono (identifiers). Taken from the `@fontsource` npm packages. The licence text of each family sits next to the files (`LICENSE-public-sans.txt`, `LICENSE-source-serif-4.txt`, `LICENSE-jetbrains-mono.txt`), copied unchanged from those packages. | SIL Open Font License 1.1. The copyright holders are named in each licence file. |

The MIT licence text for `support.js`:

```
MIT License

Copyright (c) Facebook, Inc. and its affiliates.

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

## Packages that are installed, not copied

These come from PyPI or npm when you install the project; none is copied into this repository. Their licences were read from the installed metadata on 2026-10-13, and none is copyleft.

| Package | Used for | Licence |
|---|---|---|
| PyYAML, openpyxl, SQLAlchemy, python-docx, pdfplumber (with pdfminer.six) | Reading mapping profiles, Excel, SQL, Word and PDF | MIT |
| reqif | Reading ReqIF files | Apache-2.0 |
| rdflib (optional extra `oslc`) | DOORS Next / OSLC connector | BSD-3-Clause |
| pytest, trustme (test extra) | Tests | MIT; MIT or Apache-2.0 |
| reportlab (test extra) | Building a PDF test file | BSD-style |
| react, react-dom, @babel/standalone (`prototype/vendor`, installed by `npm ci`, not committed) | Local browser test harness for the prototype | MIT |
