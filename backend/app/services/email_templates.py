"""
HTML-шаблоны email-уведомлений в фирменном стиле Ростелекома (Атомаро Purple).
"""


def status_change_email_html(
    university_name: str,
    old_stage: str,
    new_stage: str,
    contract_number: str,
) -> str:
    """
    Генерация HTML-письма о смене статуса взаимодействия.
    
    Args:
        university_name: Название ВУЗа
        old_stage: Предыдущий этап
        new_stage: Новый этап
        contract_number: Номер договора
    
    Returns:
        HTML-строка письма
    """
    html = f"""
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>RTK CRM: Статус изменён</title>
    <style>
        body {{
            font-family: system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background-color: #F5F5F7;
            color: #1C1D22;
            margin: 0;
            padding: 0;
        }}
        .container {{
            max-width: 600px;
            margin: 40px auto;
            background-color: #FFFFFF;
            border-radius: 12px;
            overflow: hidden;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
        }}
        .header {{
            background-color: #6E41F2;
            padding: 24px 32px;
            text-align: center;
        }}
        .header h1 {{
            color: #FFFFFF;
            font-size: 22px;
            font-weight: 700;
            margin: 0;
        }}
        .content {{
            padding: 32px;
        }}
        .status-block {{
            background-color: #F3E5F5;
            border-left: 4px solid #6E41F2;
            padding: 16px;
            margin: 20px 0;
            border-radius: 8px;
        }}
        .status-row {{
            margin: 12px 0;
            font-size: 16px;
            line-height: 24px;
        }}
        .status-label {{
            color: #6B6B72;
            font-weight: 400;
        }}
        .status-value {{
            color: #1C1D22;
            font-weight: 600;
        }}
        .new-stage {{
            color: #6E41F2;
            font-size: 18px;
            font-weight: 700;
        }}
        .button {{
            display: inline-block;
            background-color: #6E41F2;
            color: #FFFFFF;
            text-decoration: none;
            padding: 12px 24px;
            border-radius: 8px;
            font-weight: 600;
            font-size: 16px;
            margin-top: 24px;
        }}
        .button:hover {{
            background-color: #8A63F5;
        }}
        .footer {{
            background-color: #F5F5F7;
            padding: 20px 32px;
            text-align: center;
            font-size: 14px;
            color: #6B6B72;
            border-top: 1px solid #E0E0E5;
        }}
        .footer a {{
            color: #6E41F2;
            text-decoration: none;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>RTK CRM</h1>
        </div>
        
        <div class="content">
            <p style="font-size: 16px; line-height: 24px; margin: 0 0 20px;">
                Здравствуйте!
            </p>
            
            <p style="font-size: 16px; line-height: 24px; margin: 0 0 20px;">
                Статус взаимодействия с ВУЗом <strong>{university_name}</strong> изменён.
            </p>
            
            <div class="status-block">
                <div class="status-row">
                    <span class="status-label">ВУЗ:</span><br>
                    <span class="status-value">{university_name}</span>
                </div>
                
                <div class="status-row">
                    <span class="status-label">Договор:</span><br>
                    <span class="status-value">{contract_number}</span>
                </div>
                
                <div class="status-row">
                    <span class="status-label">Предыдущий этап:</span><br>
                    <span class="status-value">{old_stage}</span>
                </div>
                
                <div class="status-row">
                    <span class="status-label">Новый этап:</span><br>
                    <span class="new-stage">{new_stage}</span>
                </div>
            </div>
            
            <p style="font-size: 16px; line-height: 24px; margin: 20px 0 0;">
                Пожалуйста, проверьте актуальную информацию в системе RTK CRM.
            </p>
            
            <div style="text-align: center;">
                <a href="https://rtk-crm-nx4r.vercel.app/kanban" class="button">
                    Открыть в CRM
                </a>
            </div>
        </div>
        
        <div class="footer">
            <p style="margin: 0 0 8px;">
                Это письмо отправлено автоматически системой RTK CRM.
            </p>
            <p style="margin: 0;">
                © 2026 ИТ Школа Ростелекома
            </p>
        </div>
    </div>
</body>
</html>
"""
    return html
