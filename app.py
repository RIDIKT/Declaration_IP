from flask import Flask, render_template, request, send_file
from tax_calculator import calculate_tax_by_quarters
from pdf_generator import generate_pdf, build_declaration_data
import tempfile, os

app = Flask(__name__)

@app.template_filter('rub')
def format_rub(value):
    return f"{value:,.2f}".replace(",", " ")

def parse_money(raw_value, field_name):
    try:
        cleaned = raw_value.replace(' ', '').replace(',', '.')
        num = float(cleaned)
    except (ValueError, AttributeError):
        raise ValueError(f'Поле "{field_name}" должно быть числом')
    if num < 0:
        raise ValueError(f'Поле "{field_name}" не может быть отрицательным')
    return num

def validate_declaration_fields(form):
    """Проверяет поля, нужные для PDF. Возвращает список ошибок (пустой = всё ок)."""
    errors = []

    inn = form.get('inn', '').strip()
    if not inn:
        errors.append("Для декларации нужен ИНН")
    elif not inn.isdigit() or len(inn) not in (10, 12):
        errors.append("ИНН должен содержать 10 или 12 цифр")

    oktmo = form.get('oktmo', '').strip()
    if not oktmo:
        errors.append("Для декларации нужен код ОКТМО")
    elif not oktmo.isdigit() or len(oktmo) not in (8, 11):
        errors.append("Код ОКТМО должен содержать 8 или 11 цифр")

    tax_authority = form.get('tax_authority', '').strip()
    if not tax_authority:
        errors.append("Для декларации нужен код налогового органа")
    elif not tax_authority.isdigit() or len(tax_authority) != 4:
        errors.append("Код налогового органа должен содержать 4 цифры")

    fio_line1 = form.get('fio_line1', '').strip()
    fio_line2 = form.get('fio_line2', '').strip()
    if not fio_line1 or not fio_line2:
        errors.append("Для декларации нужны фамилия и имя")

    return errors


@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        errors = []
        year = None
        try:
            year = int(request.form['year'])
            if year < 2000 or year > 2100:
                errors.append("Введите корректный год")
        except (ValueError, KeyError):
            errors.append("Год должен быть числом")

        tax_system = request.form.get('tax_system', '')
        if not tax_system:
            errors.append("Выберите систему налогообложения")

        tax_rate = None
        try:
            tax_rate = float(request.form['tax_rate'])
            if tax_rate < 0 or tax_rate > 100:
                errors.append("Ставка налога должна быть от 0 до 100%")
        except (ValueError, KeyError):
            errors.append("Ставка налога должна быть числом")

        quarter_labels = {'q1': 'Доход за 1 квартал', 'q2': 'Доход за 2 квартал',
                           'q3': 'Доход за 3 квартал', 'q4': 'Доход за 4 квартал'}
        quarters_input = {}
        for field, label in quarter_labels.items():
            try:
                quarters_input[field] = parse_money(request.form.get(field, ''), label)
            except ValueError as e:
                errors.append(str(e))

        if errors:
            return render_template('index.html', errors=errors)

        result = calculate_tax_by_quarters(
            quarters_input['q1'], quarters_input['q2'],
            quarters_input['q3'], quarters_input['q4'],
            tax_rate, year
        )
        wants_pdf = 'calc_only' not in request.form

        return render_template('result.html', result=result, tax_system=tax_system, wants_pdf=wants_pdf)

    return render_template('index.html')


@app.route('/download-declaration', methods=['POST'])
def download_declaration():
    declaration_errors = validate_declaration_fields(request.form)

    # Перепроверяем расчётные поля — на случай, если они потерялись при передаче
    calc_errors = []
    year = None
    tax_rate = None
    quarters_input = {}
    try:
        year = int(request.form['year'])
    except (ValueError, KeyError):
        calc_errors.append("Некорректный год")
    try:
        tax_rate = float(request.form['tax_rate'])
    except (ValueError, KeyError):
        calc_errors.append("Некорректная ставка налога")
    for field in ('q1', 'q2', 'q3', 'q4'):
        try:
            quarters_input[field] = parse_money(request.form.get(field, ''), field)
        except ValueError as e:
            calc_errors.append(str(e))

    all_errors = declaration_errors + calc_errors

    if all_errors:
        if not calc_errors:
            # Расчёт восстановить можно — показываем ошибки на странице результата
            result = calculate_tax_by_quarters(
                quarters_input['q1'], quarters_input['q2'],
                quarters_input['q3'], quarters_input['q4'],
                tax_rate, year
            )
            return render_template('result.html', result=result,
                                    tax_system=request.form.get('tax_system', ''),
                                    wants_pdf=True, declaration_errors=all_errors)
        else:
            # Даже расчёт не восстановить — отправляем на главную
            return render_template('index.html', errors=all_errors)

    personal = {
        "inn": request.form['inn'].strip(),
        "correction_num": "0",
        "period_code": request.form.get('period_code', '34'),
        "year": year,
        "tax_authority": request.form['tax_authority'].strip(),
        "location_code": request.form.get('location_code', '120'),
        "fio_line1": request.form.get('fio_line1', '').upper(),
        "fio_line2": request.form.get('fio_line2', '').upper(),
        "fio_line3": request.form.get('fio_line3', '').upper(),
        "phone": request.form.get('phone', ''),
        "has_employees": 'has_employees' in request.form,
        "oktmo": request.form['oktmo'].strip(),
        "tax_rate": tax_rate,
    }

    calc_result = calculate_tax_by_quarters(
        quarters_input['q1'], quarters_input['q2'],
        quarters_input['q3'], quarters_input['q4'],
        tax_rate, year
    )
    data = build_declaration_data(personal, calc_result)

    tmp_path = os.path.join(tempfile.gettempdir(), f"declaration_{personal['inn']}.pdf")
    generate_pdf(data, tmp_path)

    return send_file(tmp_path, as_attachment=True, download_name="Декларация_УСН.pdf")


if __name__ == '__main__':
    app.run()