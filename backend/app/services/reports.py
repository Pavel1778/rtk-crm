from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from io import BytesIO
from datetime import datetime
from typing import List, Dict, Any


class ReportService:
    """Сервис генерации отчетов в PDF и XLSX форматах."""

    @staticmethod
    def generate_pdf_report(universities: List[Dict[str, Any]], title: str = "Отчет по вузам") -> bytes:
        """Генерация PDF отчета."""
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4)
        elements = []
        
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=18,
            textColor=colors.HexColor('#E30613'),  # Ростелеком красный
            spaceAfter=20,
            alignment=1  # Center
        )
        
        # Заголовок
        elements.append(Paragraph(title, title_style))
        elements.append(Spacer(1, 0.2*inch))
        elements.append(Paragraph(f"Дата формирования: {datetime.now().strftime('%d.%m.%Y %H:%M')}", styles['Normal']))
        elements.append(Spacer(1, 0.3*inch))
        
        # Таблица данных
        data = [["№", "ВУЗ", "Продукт", "Статус", "Менеджер", "Этап"]]
        
        for idx, uni in enumerate(universities, 1):
            data.append([
                str(idx),
                uni.get('name', ''),
                uni.get('product', ''),
                uni.get('status', ''),
                uni.get('manager_name', ''),
                uni.get('workflow_stage', '')
            ])
        
        table = Table(data, colWidths=[0.5*inch, 2*inch, 1.5*inch, 1.5*inch, 1.5*inch, 1.5*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#E30613')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('FONTSIZE', (0, 1), (-1, -1), 10),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey]),
        ]))
        
        elements.append(table)
        elements.append(Spacer(1, 0.5*inch))
        
        # Итоговая статистика
        stats_data = [
            ["Всего вузов", str(len(universities))],
            ["С подписанной лицензией", str(sum(1 for u in universities if u.get('license_signed')))],
            ["Активные проекты", str(sum(1 for u in universities if u.get('status') in ['Внедрение', 'Обучение', 'Ведение занятий']))]
        ]
        
        stats_table = Table(stats_data, colWidths=[2*inch, 1*inch])
        stats_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.lightblue),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
        ]))
        
        elements.append(Paragraph("Статистика:", styles['Heading2']))
        elements.append(Spacer(1, 0.2*inch))
        elements.append(stats_table)
        
        doc.build(elements)
        pdf_bytes = buffer.getvalue()
        buffer.close()
        return pdf_bytes

    @staticmethod
    def generate_xlsx_report(universities: List[Dict[str, Any]]) -> bytes:
        """Генерация XLSX отчета."""
        from openpyxl import Workbook
        from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
        
        wb = Workbook()
        ws = wb.active
        ws.title = "ВУЗы"
        
        # Стили
        header_font = Font(bold=True, color="FFFFFF", size=12)
        header_fill = PatternFill(start_color="E30613", end_color="E30613", fill_type="solid")
        cell_alignment = Alignment(horizontal="center", vertical="center")
        thin_border = Border(
            left=Side(style='thin'),
            right=Side(style='thin'),
            top=Side(style='thin'),
            bottom=Side(style='thin')
        )
        
        # Заголовки
        headers = ["№", "ВУЗ", "Vendor", "Продукт", "Договор", "Лицензия", 
                   "Год окончания", "Статус", "Менеджер", "Ответственный в ВУЗе", "Комментарий"]
        
        for col, header in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col, value=header)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = cell_alignment
            cell.border = thin_border
        
        # Данные
        for idx, uni in enumerate(universities, 2):
            row_data = [
                idx - 1,
                uni.get('name', ''),
                uni.get('vendor', ''),
                uni.get('product', ''),
                uni.get('contract_number', ''),
                'Да' if uni.get('license_signed') else 'Нет',
                uni.get('license_expiry_year', ''),
                uni.get('status', ''),
                uni.get('manager_name', ''),
                uni.get('university_responsible', ''),
                uni.get('comment', '')
            ]
            
            for col, value in enumerate(row_data, 1):
                cell = ws.cell(row=idx, column=col, value=value)
                cell.alignment = cell_alignment
                cell.border = thin_border
                
                # Чередование цветов строк
                if idx % 2 == 0:
                    cell.fill = PatternFill(start_color="F0F0F0", end_color="F0F0F0", fill_type="solid")
        
        # Автоширина колонок
        for column in ws.columns:
            max_length = 0
            column_letter = column[0].column_letter
            for cell in column:
                try:
                    if len(str(cell.value)) > max_length:
                        max_length = len(str(cell.value))
                except:
                    pass
            adjusted_width = min(max_length + 2, 50)
            ws.column_dimensions[column_letter].width = adjusted_width
        
        # Сохранение
        buffer = BytesIO()
        wb.save(buffer)
        xlsx_bytes = buffer.getvalue()
        buffer.close()
        return xlsx_bytes
