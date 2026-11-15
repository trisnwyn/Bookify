// Bookify v2 OCR capability fixture.
//
// Authored synthetic content. No third-party text, no third-party images, no
// private source. Page 1 is prose with an image-borne table, page 2 is a fully
// image-only table, page 3 is a deliberately degraded image that must remain
// unresolved, page 4 carries Vietnamese text so the `vie` data is exercised.
//
// Build with fixtures/ocr-capability/build_fixture.py; image paths are created
// in fixtures/ocr-capability/build before this file is compiled.
#set document(title: "OCR capability fixture", author: "Bookify")
#set page(paper: "a4", margin: (x: 20mm, y: 20mm))
#set text(font: "Spectral", size: 10.5pt, fill: rgb("#111111"), hyphenate: false)
#set par(justify: true, leading: 0.65em)
#set heading(numbering: none)
#show heading: set text(size: 16pt, weight: "semibold")

= Trial balance and the ledger

An opening trial balance lists every ledger account and its balance at a chosen
date. It is not a financial statement. It is a checking device, and a modest
one: equal debit and credit columns show that the clerk has avoided the simplest
class of posting error. Equality does not prove that each entry reached the
correct account, that no entry was posted twice on the same side, or that an
omission was not balanced by a second mistake somewhere else.

The table below was supplied as a page image. Read it as evidence rather than as
a statement of position. The figures come from a practice set, not from a real
business, and the account names are deliberately plain so that a reader can
follow the arithmetic without a chart of accounts. A clerk who copies a figure
from this image is making a new record, not recovering the original one.

#v(4mm)

#align(center)[
  #image("../build/trial-balance.png", width: 100%)
  #v(1.5mm)
  #text(size: 9pt)[Figure 1. Trial balance supplied as a page image.]
]

#pagebreak()

#align(center)[
  #image("../build/cash-receipts.png", width: 100%)
]

#pagebreak()

#image("../build/trial-balance-45.png", width: 100%)

#pagebreak()

= Kiểm tra dữ liệu tiếng Việt

Bảng cân đối thử là bản liệt kê số dư của từng tài khoản tại một ngày đã chọn.
Nó không phải là báo cáo tài chính. Nếu tổng bên Nợ bằng tổng bên Có, người ghi
sổ chỉ mới tránh được loại lỗi đơn giản nhất. Con số trong bảng là dữ liệu tổng
hợp, không phải số liệu của một doanh nghiệp thật.
