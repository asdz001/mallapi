from openpyxl import Workbook

def generate_failed_excel(failed_rows, save_path):
    wb = Workbook()
    ws = wb.active
    ws.title = "실패항목"

    if not failed_rows:
        return None

    headers = list(failed_rows[0].keys())
    ws.append(headers)

    for row in failed_rows:
        ws.append([row.get(col, "") for col in headers])

    wb.save(save_path)
    return save_path
