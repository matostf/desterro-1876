# Provenance

One entry per image file in this repository. Format: what it is, who holds
the original, where the record is, how it was obtained, on what basis it can
be reused.

## The work

**Title (as printed):** *Planta topographica da Cidade do Desterro, levantada
por ordem e na presidencia da Provincia de Santa Catharina do Ill.mo e Ex.mo
Sr. Dr. Alfredo d'Escragnolle Taunay pelos Engenheiros Major Dr. Antonio
Florencio Pereira do Lago e Carlos Othom Schappal. Anno de 1876.*

**Authors:** Antonio Florencio Pereira do Lago (engineer, major); Carlos Othom
Schappal (engineer); commissioned by Alfredo d'Escragnolle Taunay (president
of the province of Santa Catarina, 1876–1877; died 1899).

**Date:** 1876. **Place:** Desterro, today Florianópolis, Santa Catarina, Brazil.

**Rights basis:** public domain by age. Published in 1876; under Brazilian
Law 9.610/1998 art. 41 economic rights last 70 years from the author's death,
and no author of an 1876 survey can have died within the last 70 years.
Faithful reproductions of a public-domain two-dimensional work do not create a
new copyright in the reproduction.

## `data/raw/` — UFSC scans (four files)

| file | content | size on server |
|---|---|---|
| `Mapa_Cartoes_CEMIf00016A_superior.tif` | recto, upper half | 25.14 MB |
| `Mapa_Cartoes_CEMIf00016B_inferior.tif` | recto, lower half | 25.17 MB |
| `Mapa_Cartoes21-01-07CEMIv00016A.tif` | verso, upper half (library stamps only) | 18.57 MB |
| `Mapa_Cartoes21-01-07CEMIv00016B.tif` | verso, lower half (library stamps only) | 17.04 MB |

- **Holding institution:** Universidade Federal de Santa Catarina, Biblioteca
  Universitária, Seção de Coleções Especiais. Call number on the sheet label:
  `912.43(816.406) M297`; accession stamp on verso: `SC M 155`.
- **Record:** Repositório Institucional da UFSC, collection "2.3.3 Mapas e
  cartões", handle <https://repositorio.ufsc.br/handle/123456789/220180>
  (accessioned 2021-02-18). Saved copies of the record page and of the full
  Dublin Core view are in `docs/source-pages/` as downloaded on 2026-08-19.
- **Repository abstract (translated):** "Digitisation of [title]. Because its
  dimensions exceed an A4 sheet, the digitisation is split into two images
  (upper and lower part)."
- **Scan characteristics:** 3510 × 2550 px, RGB, 300 dpi, scanner rulers
  visible on the bed. The recto halves overlap by roughly 780 px (the legend
  "Observações" and the road network around the Olaria appear in both).
- **Obtained:** downloaded from the repository on 2026-08-19; file names kept
  exactly as published. The TIFFs in this repository are the originals
  (LZW-compressed), not re-encoded.

## `data/reference/cart516191.jpg` — Biblioteca Nacional scan

- **Holding institution:** Fundação Biblioteca Nacional (Rio de Janeiro),
  Divisão de Cartografia. Identifier `cart516191` (the BN digital-object
  naming scheme; the same string appears in the image URL of the BN digital
  collection).
- **Record:** Biblioteca Digital Luso-Brasileira,
  <https://bdlb.bn.gov.br/acervo/handle/20.500.12156.3/40502>, catalogued as
  "Planta topográphica da cidade do Desterro".
- **Scan characteristics:** 4140 × 4866 px JPEG, single image of the whole
  sheet, sepia-toned reproduction.
- **Obtained:** downloaded on 2026-08-19. The BN site returns HTTP 403 to
  non-browser clients, so the catalogue page could not be re-fetched
  programmatically on 2026-09-18 to quote its rights field verbatim; the
  reuse basis is the public-domain status of the work itself.
- **Role here:** independent ground truth. It was digitised from a different
  physical copy, on different equipment, so agreement between it and the UFSC
  stitch cannot come from a shared error.

## `docs/` — derived previews

All files in `docs/*.jpg` are down-sampled or cropped versions of the images
above, produced by this project; same rights basis. `docs/source-pages/` holds
the UFSC catalogue pages saved by the browser (HTML plus assets) as evidence
of the record at download time.
