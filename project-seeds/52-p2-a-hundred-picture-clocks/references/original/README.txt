Original animation extraction

Source: https://chatgpt.com/share/6ae1379a-9dc8-83ed-8fee-9aca58017cc7
Extracted from the authenticated Chrome tab using read-only DOM inspection.

Files:
- animation.js: exact textContent of the original inline animation script. All six original animation functions are included. No rewriting, conversion, recording or reimplementation.
- animation.css: exact textContent of its animation-specific style element.
- animation-dom.html: DOM serialization of the original #ntt-preview element. Serialization may differ from the original source formatting; current caption/attributes reflect the captured state.
- rendered-document.html: complete DOM serialization of the embedded presentation document, including host-injected styles and scripts. This is not a downloaded HTTP response and is not certified byte-identical to original server HTML.
- extracted-blocks.json: original script/style textContent plus metadata, encoded in JSON. External host script URLs are recorded, not downloaded.
- provenance.json: extraction details and verification scope.
- SHA256SUMS.txt: hashes of all payload files except this manifest itself.

No image, video, audio, source or stylesheet-link assets were present in the animation frame. Its six animations draw procedurally to canvas. Four external scripts are host/framework resources referenced by rendered-document.html; their bytes were not acquired. The HTML is preserved without URL rewriting and is not certified fully offline.

Verification: animation.js was read back from disk and compared directly to a fresh extraction of the live animation script; equality passed. ZIP entry contents are verified against saved payload hashes. No original HTTP response bytes or server-issued hashes were available, so binary identity to a server original remains unverified. DOM text is stored as UTF-8 without BOM.

To inspect the original animation code, open animation.js. To view the captured presentation, open rendered-document.html in a browser; host-specific functionality or external resources may require network access.
