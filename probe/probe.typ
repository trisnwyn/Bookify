#set document(title: "Bookify stack probe", author: "Bookify")
#set page(paper: "a4", margin: (x: 60pt, y: 62pt))
#set text(
  font: ("Spectral", "Noto Serif CJK JP"),
  size: 10.1pt,
  lang: "en",
  region: "GB",
)
#set par(justify: true, leading: 1.52em)
#show regex("[\p{Hiragana}\p{Katakana}\p{Han}\u{3000}-\u{303F}\u{FF00}-\u{FFEF}]"): set text(
  font: "Noto Serif CJK JP",
  weight: 500,
)
#show math.equation: set text(font: "STIX Two Math", size: 12pt)

#set heading(numbering: none)
#heading(level: 1, "Stack probe: scripts, fallback and maths")

The house face is Spectral. This paragraph is set in it, justified, with British
spelling and a few special characters: em dash — en dash – curly quotes ‘and’,
arrows →, inequality ≤ ≥, and a sum ∑.

= Tiếng Việt

Tiếng Việt có đủ dấu: ế ộ ữ đ ạ ỹ ỡ ư ơ ằ ắ ẳ ẵ ặ ầ ấ ẩ ẫ ậ è é ẻ ẽ ẹ ì í ỉ ĩ ị ò ó ỏ õ ọ
ù ú ủ ũ ụ ỳ ý ỷ ỹ ỵ. Câu này kiểm tra việc xuống dòng và căn đều hai bên trong một
đoạn văn dài, để chắc rằng dấu tiếng Việt vẫn nằm đúng chỗ sau khi ngắt dòng.

= 日本語

日本語の文章は単語の間に空白がないため、行の折り返しが正しく行われるかを確認します。
漢字とひらがなとカタカナが混在していても、行が余白を越えず、文節の切れ目で自然に折り返される必要があります。
この段落は、その確認のための十分な長さを持っています。

= Equation

$
  sum_(i=1)^n x_i = (n (n + 1)) / 2,
  quad
  sqrt(a^2 + b^2) <= c
$
