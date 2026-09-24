"""Проверка генераторов XLSX, XLS и PDF без запуска приложения."""

import sys
from io import BytesIO
from pathlib import Path
from zipfile import ZipFile

from openpyxl import load_workbook

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.services.excel_export import generate_pdf, generate_xls, generate_xlsx

SAMPLE = [
    {
        "university_name": "МГТУ им. Н. Э. Баумана",
        "direction_name": "Разработка ПО",
        "product_name": "AI Studio",
        "stage_name": "Коммуникация",
        "assigned_kam_name": "Иванов И. И.",
        "contract_number": "РТК-2026-001",
        "contract_date": "2026-09-22",
    }
]


def main() -> None:
    xlsx = generate_xlsx(SAMPLE).read()
    assert xlsx.startswith(b"PK") and len(xlsx) > 0
    with ZipFile(BytesIO(xlsx)) as archive:
        assert "xl/sharedStrings.xml" in archive.namelist() or "xl/worksheets/sheet1.xml" in archive.namelist()
    workbook = load_workbook(BytesIO(xlsx), read_only=True)
    assert workbook.active["A2"].value == SAMPLE[0]["university_name"]
    print(f"✓ XLSX {len(xlsx) // 1024} KB")

    xls = generate_xls(SAMPLE).read()
    assert xls.startswith(b"\xd0\xcf\x11\xe0") and len(xls) > 0
    print(f"✓ XLS {len(xls) // 1024} KB")

    pdf = generate_pdf(SAMPLE).read()
    assert pdf.startswith(b"%PDF") and b"DejaVu" in pdf
    print(f"✓ PDF {len(pdf) // 1024} KB")


if __name__ == "__main__":
    main()
