import re


def append_to_html(item, html_file):
    """
    HTML dosyasına eklerken:
    - Markdown işaretlerini temizler (#, *, **)
    - | ve --- ile yazılmış tablo varsa gerçek HTML <table> yapar
    - Satır sonlarını <br> ile korur
    """
    text = item["analysis"]

    # Tablo var mı kontrol et
    table_blocks = []
    lines = text.split("\n")
    non_table_lines = []
    current_table = []

    for line in lines:
        if "|" in line:
            current_table.append(line)
        else:
            if current_table:
                table_blocks.append(current_table)
                current_table = []
            non_table_lines.append(line)
    if current_table:
        table_blocks.append(current_table)

    # Tabloyu HTML yap
    html_tables = []
    for table in table_blocks:
        html_table = ["<table border='1' cellspacing='0' cellpadding='5'>"]
        for i, row in enumerate(table):
            cells = [c.strip() for c in row.split("|") if c.strip()]
            if i == 0 or all(re.match(r"^-+$", c) for c in cells):
                html_table.append("<tr>" + "".join(f"<th>{c}</th>" for c in cells) + "</tr>")
            else:
                html_table.append("<tr>" + "".join(f"<td>{c}</td>" for c in cells) + "</tr>")
        html_table.append("</table>")
        html_tables.append("\n".join(html_table))

    # Markdown işaretlerini temizle
    clean_text = re.sub(r"[*#]+", "", "\n".join(non_table_lines)).strip()
    clean_text = clean_text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    clean_text = clean_text.replace("\n", "<br>")

    # HTML yaz
    with open(html_file, "a", encoding="utf-8") as f:
        f.write(f"<h2>{item['program_name']}</h2>\n")
        f.write(f"<p><strong>Başvuru Koşulları:</strong> {item['applicant_requirements']}</p>\n")
        f.write(f"<p>{clean_text}</p>\n")
        for table_html in html_tables:
            f.write(f"{table_html}\n")
        f.write("<hr>\n\n")


def init_html(html_file):
    """HTML dosyasını başlatır."""
    with open(html_file, "w", encoding="utf-8") as f:
        f.write("<!DOCTYPE html>\n<html lang='tr'>\n<head>\n<meta charset='utf-8'>\n")
        f.write("<title>Ar-Ge Program Analizleri</title>\n</head>\n<body>\n")
        f.write("<h1>TÜBİTAK Ar-Ge Program Analizleri</h1>\n")


def close_html(html_file):
    """HTML dosyasını kapatır."""
    with open(html_file, "a", encoding="utf-8") as f:
        f.write("</body>\n</html>")
