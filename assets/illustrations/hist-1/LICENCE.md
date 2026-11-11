# Licence evidence — hist-1

Frozen local copy: `assets/illustrations/hist-1/original.jpg`
SHA-256: `e524d2684a642ba8035d1ea535cbdd65bfd6605bca94328d319a04028eee9a94`
Size: 134,827 bytes; 1080 × 1332 px; JPEG (RGB).
Retrieved: 2026-11-10.

## Origin

- File page: https://commons.wikimedia.org/wiki/File:Macarthur_hirohito.jpg
- Direct file: https://upload.wikimedia.org/wikipedia/commons/d/d4/Macarthur_hirohito.jpg
- Title: `File:Macarthur hirohito.jpg`
- Subject: Emperor Hirohito and General Douglas MacArthur at their first meeting,
  U.S. Embassy, Tokyo, 27 September 1945.
- Creator: Gaetano Faillace (photographer).
- Source credit on Commons: United States Army photograph.

## Licence

- Commons licence template: `PD-USGov-Military-Army`
  (https://commons.wikimedia.org/wiki/Template:PD-USGov-Military-Army).
- API `extmetadata` at retrieval: `LicenseShortName = Public domain`,
  `UsageTerms = Public domain`, `Copyrighted = False`, `License = pd`.
- Rationale: the photograph was taken by a US Army photographer as part of
  official duties, so it is a work of the US federal government and in the
  public domain in the United States. Commons hosts it under the Army
  public-domain tag above.

## Evidence trail

1. Metadata only: MediaWiki API `action=query&prop=imageinfo&iiprop=url|size|mime|extmetadata`
   for `File:Macarthur hirohito.jpg` returned the URL, dimensions, MIME type
   and the licence values quoted above.
2. Metadata only: the parsed file-page wikitext contains
   `{{PD-USGov-Military-Army}}` and the Information template fields above.
3. Metadata only: the rendered file page was fetched as HTML (123,414 bytes,
   no image bytes) and its licensing table reports both the short and long
   licence name as “Public domain”, with the Army tag still present.
4. Exactly one image download: a single `curl` GET of the direct file URL above,
   written straight to `assets/illustrations/hist-1/original.jpg`. No second
   fetch, no thumbnail variant, no paid generation and no retouching.
5. The frozen file's SHA-256 was computed after that download and recorded in
   `record.yaml`; the record and this file now carry the same hash.
6. Integrity cross-check: the local file's SHA-1
   (`8d4c6c3c1d4d3ed5d33d557adb2369ee030aad32`) and byte size (134,827) match
   the `imageinfo` values Commons returned for the same file, so the frozen
   copy is the file covered by the licence tag above.

The one-download rule covers the image bytes. The API and HTML requests above
are metadata requests; they returned no image content.
