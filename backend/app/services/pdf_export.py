"""
Генерация PDF-отчётов с помощью ReportLab.
Используется для экспорта отчётов по взаимодействиям в формате PDF.
"""
from io import BytesIO
from typing import List, Dict, Any
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, cm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from loguru import logger

from app.core.config import settings


def generate_pdf_report(data: List[Dict[str, Any]], title: str = "Отчёт по взаимодействиям") -> bytes:
    """
    Генерация PDF-отчёта с таблицей взаимодействий.

    :param data: Список словарей с данными взаимодействий
    :param title: Заголовок отчёта
    :return: Байты PDF-файла
    """
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=2 * cm,
        leftMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
    )

    elements = []

    # Стили
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=18,
        textColor=colors.HexColor('#6E41F2'),
        spaceAfter=30,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold',
    )

    # Заголовок
    elements.append(Paragraph(title, title_style))
    elements.append(Spacer(1, 0.3 * inch))

    # Данные таблицы
    if not data:
        elements.append(Paragraph("Нет данных для отображения", styles['Normal']))
    else:
        # Заголовки колонок
        headers = list(data[0].keys())
        table_data = [headers]

        for row in data:
            table_data.append([str(row.get(h, '')) for h in headers])

        # Создание таблицы
        table = Table(table_data, colWidths=[2.5 * inch] * len(headers))
        table.setStyle(TableStyle([
            # Заголовок
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#6E41F2')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),

            # Чередование цветов строк
            ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#F5F5F7')),
            ('BACKGROUND', (0, 2), (-1, -1), colors.white),
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#E0E0E5')),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 10),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.HexColor('#F5F5F7'), colors.white]),
        ]))

        elements.append(table)

    # Построение документа
    doc.build(elements)
    pdf_data = buffer.getvalue()
    buffer.close()

    logger.info(f"PDF-отчёт '{title}' сгенерирован ({len(pdf_data)} байт)")
    return pdf_data


def generate_dashboard_pdf(kpi: Dict[str, Any], charts_data: Dict[str, Any]) -> bytes:
    """
    Генерация PDF-дашборда с KPI и графиками.

    :param kpi: Словарь с KPI метриками
    :param charts_data: Данные для графиков
    :return: Байты PDF-файла
    """
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        orientation='landscape',
        rightMargin=1.5 * cm,
        leftMargin=1.5 * cm,
        topMargin=1.5 * cm,
        bottomMargin=1.5 * cm,
    )

    elements = []

    # Стили
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'DashboardTitle',
        parent=styles['Heading1'],
        fontSize=20,
        textColor=colors.HexColor('#6E41F2'),
        spaceAfter=20,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold',
    )

    kpi_style = ParagraphStyle(
        'KPI',
        parent=styles['Normal'],
        fontSize=14,
        textColor=colors.HexColor('#1C1D22'),
        spaceAfter=10,
        alignment=TA_LEFT,
        fontName='Helvetica-Bold',
    )

    # Заголовок
    elements.append(Paragraph("Дашборд RTK CRM", title_style))
    elements.append(Spacer(1, 0.2 * inch))

    # KPI карточки
    elements.append(Paragraph("Ключевые показатели:", kpi_style))
    kpi_table_data = [
        ["Всего взаимодействий", str(kpi.get('total_interactions', 0))],
        ["Активных", str(kpi.get('active_interactions', 0))],
        ["Просроченных", str(kpi.get('stale_interactions', 0))],
        ["ВУЗов", str(kpi.get('universities_count', 0))],
        ["Продуктов", str(kpi.get('products_count', 0))],
        ["КАМов", str(kpi.get('kam_count', 0))],
    ]

    kpi_table = Table(kpi_table_data, colWidths=[3 * inch, 1.5 * inch])
    kpi_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#F5F5F7')),
        ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#E0E0E5')),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 11),
        ('ROWBACKGROUNDS', (0, 0), (-1, -1), [colors.HexColor('#F3E5F5'), colors.white]),
    ]))

    elements.append(kpi_table)
    elements.append(Spacer(1, 0.3 * inch))

    # Примечание о графиках
    note_style = ParagraphStyle(
        'Note',
        parent=styles['Italic'],
        fontSize=10,
        textColor=colors.HexColor('#6B6B72'),
        alignment=TA_CENTER,
    )
    elements.append(Paragraph(
        "Графики визуализируются на фронтенде с использованием Recharts. "
        "Для экспорта графиков используйте функцию скачивания PNG/PDF на дашборде.",
        note_style
    ))

    # Построение документа
    doc.build(elements)
    pdf_data = buffer.getvalue()
    buffer.close()

    logger.info(f"PDF-дашборд сгенерирован ({len(pdf_data)} байт)")
    return pdf_data
