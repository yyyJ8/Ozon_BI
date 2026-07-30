"""
将 all_tables_with_data.txt 转为 markdown 表格格式
"""
import re
import os

INPUT = "scripts/output/ozon_actual_data_20260730_160537.txt"
OUTPUT = "scripts/output/ozon_tables_with_data.md"


def parse_and_convert():
    with open(INPUT, "r", encoding="utf-8") as f:
        lines = f.readlines()

    md_lines = []
    current_table = None
    current_section = None  # 'pg' or 'mysql'
    rows = []  # [(field, comment, ex1, ex2)]
    in_table = False

    for line in lines:
        line = line.rstrip("\n")

        # Section headers
        if line.startswith("PostgreSQL"):
            current_section = "pg"
            md_lines.append(f"\n# {line}")
            md_lines.append("")
            continue
        if line.startswith("MySQL"):
            current_section = "mysql"
            md_lines.append(f"\n# {line}")
            md_lines.append("")
            continue

        # Table delimiter
        if line.startswith("──") or line.startswith("══"):
            continue

        # New table
        m = re.match(r"【(.+?)】", line)
        if m:
            # flush previous table
            if rows:
                write_table(md_lines, rows)
                rows = []
            current_table = m.group(1)
            md_lines.append(f"\n## {current_table}")
            md_lines.append("")
            in_table = True
            continue

        # Field line
        m = re.match(r"  (\w+)(?:\s+--\s+(.+?))?$", line)
        if m:
            field = m.group(1)
            comment = m.group(2) or ""
            rows.append([field, comment, "", ""])
            continue

        # Example lines
        m_ex1 = re.match(r"    → 例1: (.+)$", line)
        m_ex2 = re.match(r"    → 例2: (.+)$", line)
        m_single = re.match(r"    → \[(.+)\]$", line)

        if rows:
            if m_ex1:
                rows[-1][2] = m_ex1.group(1)
            elif m_ex2:
                rows[-1][3] = m_ex2.group(1)
            elif m_single:
                rows[-1][2] = m_single.group(1)
                rows[-1][3] = "(同上)"

    # flush last table
    if rows:
        write_table(md_lines, rows)

    # Save
    with open(OUTPUT, "w", encoding="utf-8") as f:
        f.write("\n".join(md_lines))
    print(f"Done: {OUTPUT}")


def write_table(md_lines, rows):
    md_lines.append("| 字段 | 说明 | 例1 | 例2 |")
    md_lines.append("|------|------|-----|-----|")
    for field, comment, ex1, ex2 in rows:
        # escape pipe in values
        ex1 = ex1.replace("|", "\\|")[:100]
        ex2 = ex2.replace("|", "\\|")[:100]
        comment = comment.replace("|", "\\|")
        md_lines.append(f"| `{field}` | {comment} | {ex1} | {ex2} |")
    md_lines.append("")


if __name__ == "__main__":
    os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    parse_and_convert()
