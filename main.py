import sys
import datetime
import json
import mysql.connector
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QLineEdit, QPushButton, QLabel, QTableWidget, QTableWidgetItem,
    QMessageBox, QDialog, QHBoxLayout, QDateEdit, QListWidget, QFileDialog
)
from PyQt6.QtCore import QDate
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
import xlsxwriter

# Конфигурация подключения к базе данных
DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "1234",  # Замените на ваш пароль
    "database": "work_time_db",
}

# Класс для работы с базой данных
class Database:
    def __init__(self):
        try:
            self.connection = mysql.connector.connect(**DB_CONFIG)
            self.cursor = self.connection.cursor(dictionary=True)
        except mysql.connector.Error as e:
            QMessageBox.critical(None, "Ошибка подключения к базе данных", f"Не удалось подключиться к базе данных: {e}")
            sys.exit(1)

    def authenticate_user(self, username, password):
        query = "SELECT * FROM users WHERE username = %s AND password = %s"
        self.cursor.execute(query, (username, password))
        return self.cursor.fetchone()

    def get_user_work_time(self, user_id):
        query = "SELECT date, hours FROM work_time WHERE user_id = %s ORDER BY date"
        self.cursor.execute(query, (user_id,))
        return self.cursor.fetchall()

    def add_work_time(self, user_id, date, hours):
        query = "INSERT INTO work_time (user_id, date, hours) VALUES (%s, %s, %s)"
        self.cursor.execute(query, (user_id, date, hours))
        self.connection.commit()

    def get_all_work_time(self):
        query = """
        SELECT users.full_name, work_time.date, work_time.hours
        FROM work_time
        JOIN users ON work_time.user_id = users.id
        ORDER BY users.full_name, work_time.date
        """
        self.cursor.execute(query)
        return self.cursor.fetchall()

    def get_hours_by_date(self, user_id, date):
        query = "SELECT SUM(hours) as total_hours FROM work_time WHERE user_id = %s AND date = %s"
        self.cursor.execute(query, (user_id, date))
        result = self.cursor.fetchone()
        return result["total_hours"] or 0

    def register_user(self, username, password, full_name, role):
        query = "INSERT INTO users (username, password, full_name, role) VALUES (%s, %s, %s, %s)"
        self.cursor.execute(query, (username, password, full_name, role))
        self.connection.commit()

    def get_all_employees(self):
        query = "SELECT id, full_name FROM users WHERE role = 'employee'"
        self.cursor.execute(query)
        return self.cursor.fetchall()

    def get_work_time_for_period(self, user_id, start_date, end_date):
        query = """
        SELECT date, hours FROM work_time
        WHERE user_id = %s AND date BETWEEN %s AND %s
        ORDER BY date
        """
        self.cursor.execute(query, (user_id, start_date, end_date))
        return self.cursor.fetchall()

    def save_report(self, user_ids, start_date, end_date, report_data):
        try:
            # Преобразуем данные отчета в JSON
            report_json = json.dumps(report_data, default=str)

            # Сохраняем в таблицу `reports`
            query = """
            INSERT INTO reports (user_id, start_date, end_date, report_data)
            VALUES (%s, %s, %s, %s)
            """
            for user_id in user_ids:
                self.cursor.execute(query, (user_id, start_date, end_date, report_json))
            self.connection.commit()
            QMessageBox.information(None, "Успех", "Отчет успешно сохранен в базе данных")
        except mysql.connector.Error as e:
            QMessageBox.critical(None, "Ошибка сохранения", f"Ошибка при сохранении отчета в базу данных: {e}")
            print(f"Ошибка базы данных: {e}")
        except Exception as e:
            QMessageBox.critical(None, "Ошибка", f"Непредвиденная ошибка: {e}")
            print(f"Непредвиденная ошибка: {e}")


# Окно авторизации
class LoginWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Авторизация")
        self.setGeometry(100, 100, 300, 200)

        self.db = Database()

        self.username_input = QLineEdit(self)
        self.username_input.setPlaceholderText("Имя пользователя")
        self.username_input.setGeometry(50, 20, 200, 30)
        self.password_input = QLineEdit(self)
        self.password_input.setPlaceholderText("Пароль")
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.setGeometry(50, 60, 200, 30)

        self.login_button = QPushButton("Войти", self)
        self.login_button.setGeometry(50, 100, 100, 30)
        self.login_button.clicked.connect(self.authenticate)

        self.register_button = QPushButton("Регистрация", self)
        self.register_button.setGeometry(160, 100, 100, 30)
        self.register_button.clicked.connect(self.open_registration_window)

    def authenticate(self):
        username = self.username_input.text()
        password = self.password_input.text()

        user = self.db.authenticate_user(username, password)
        if user:
            self.open_main_window(user)
        else:
            QMessageBox.warning(self, "Ошибка", "Неверное имя пользователя или пароль")

    def open_main_window(self, user):
        self.main_window = MainWindow(user)
        self.main_window.show()
        self.close()

    def open_registration_window(self):
        self.registration_window = RegistrationWindow(self)
        self.registration_window.show()


# Окно регистрации
class RegistrationWindow(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Регистрация")
        self.setGeometry(100, 100, 300, 300)

        self.db = Database()

        self.full_name_input = QLineEdit(self)
        self.full_name_input.setPlaceholderText("ФИО")
        self.full_name_input.setGeometry(50, 20, 200, 30)

        self.username_input = QLineEdit(self)
        self.username_input.setPlaceholderText("Имя пользователя")
        self.username_input.setGeometry(50, 60, 200, 30)

        self.password_input = QLineEdit(self)
        self.password_input.setPlaceholderText("Пароль")
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.setGeometry(50, 100, 200, 30)

        self.role_input = QLineEdit(self)
        self.role_input.setPlaceholderText("Роль (employee/manager)")
        self.role_input.setGeometry(50, 140, 200, 30)

        self.register_button = QPushButton("Зарегистрировать", self)
        self.register_button.setGeometry(100, 200, 100, 30)
        self.register_button.clicked.connect(self.register_user)

    def register_user(self):
        full_name = self.full_name_input.text()
        username = self.username_input.text()
        password = self.password_input.text()
        role = self.role_input.text()

        if not full_name or not username or not password or not role:
            QMessageBox.warning(self, "Ошибка", "Заполните все поля")
            return

        if role not in ["employee", "manager"]:
            QMessageBox.warning(self, "Ошибка", "Роль должна быть 'employee' или 'manager'")
            return

        self.db.register_user(username, password, full_name, role)
        QMessageBox.information(self, "Успех", "Пользователь успешно зарегистрирован")
        self.close()


# Главное окноы
class MainWindow(QMainWindow):
    def __init__(self, user):
        super().__init__()
        self.user = user
        self.db = Database()

        self.setWindowTitle(f"Система учета рабочего времени - {user['role'].capitalize()}")
        self.setGeometry(100, 100, 600, 400)

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QVBoxLayout()
        self.central_widget.setLayout(self.layout)

        self.label = QLabel(f"Добро пожаловать, {self.user['full_name']}!")
        self.layout.addWidget(self.label)
        self.logout_button = QPushButton("Выход")
        self.logout_button.clicked.connect(self.logout)
        self.layout.addWidget(self.logout_button)

        if user["role"] == "employee":
            self.init_employee_ui()
        elif user["role"] == "manager":
            self.init_manager_ui()

    def init_employee_ui(self):
        self.time_input = QLineEdit()
        self.time_input.setPlaceholderText("Введите отработанное время (часы)")
        self.layout.addWidget(self.time_input)

        self.submit_button = QPushButton("Отправить")
        self.submit_button.clicked.connect(self.submit_time)
        self.layout.addWidget(self.submit_button)

        self.table = QTableWidget(0, 2)
        self.table.setHorizontalHeaderLabels(["Дата", "Время (ч)"])
        self.layout.addWidget(self.table)

        self.load_employee_data()

    def submit_time(self):
        time = self.time_input.text()

        if not time.isdigit():
            QMessageBox.warning(self, "Ошибка", "Введите корректное количество часов (целое число)")
            return

        hours = int(time)

        if hours < 1 or hours > 24:
            QMessageBox.warning(self, "Ошибка", "Введите количество часов от 1 до 24")
            return

        date = datetime.date.today().strftime("%Y-%m-%d")
        work_time_today = self.db.get_hours_by_date(self.user["id"], date)

        if work_time_today + hours > 24:
            QMessageBox.warning(self, "Ошибка", f"Общее количество часов за день не может превышать 24")
            return

        self.db.add_work_time(self.user["id"], date, hours)
        self.load_employee_data()
        self.time_input.clear()
        QMessageBox.information(self, "Успех", "Рабочее время добавлено!")

    def load_employee_data(self):
        self.table.setRowCount(0)
        work_time = self.db.get_user_work_time(self.user["id"])
        for record in work_time:
            row_position = self.table.rowCount()
            self.table.insertRow(row_position)
            date_str = record["date"].strftime("%Y-%m-%d")
            self.table.setItem(row_position, 0, QTableWidgetItem(date_str))
            self.table.setItem(row_position, 1, QTableWidgetItem(str(record["hours"])))

    def init_manager_ui(self):
        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["Сотрудник", "Дата", "Время (ч)"])
        self.layout.addWidget(self.table)

        self.report_button = QPushButton("Создать отчет")
        self.report_button.clicked.connect(self.open_report_dialog)
        self.layout.addWidget(self.report_button)

        self.load_manager_data()

    def load_manager_data(self):
        self.table.setRowCount(0)
        work_time = self.db.get_all_work_time()
        for record in work_time:
            row_position = self.table.rowCount()
            self.table.insertRow(row_position)
            date_str = record["date"].strftime("%Y-%m-%d")
            self.table.setItem(row_position, 0, QTableWidgetItem(record["full_name"]))
            self.table.setItem(row_position, 1, QTableWidgetItem(date_str))
            self.table.setItem(row_position, 2, QTableWidgetItem(str(record["hours"])))

    def open_report_dialog(self):
        self.report_dialog = ReportDialog(self.db)
        self.report_dialog.show()

    def logout(self):
        self.login_window = LoginWindow()
        self.login_window.show()
        self.close()


# Диалог создания отчета
class ReportDialog(QDialog):
    def __init__(self, db):
        super().__init__()
        self.db = db

        self.setWindowTitle("Создание отчета")
        self.setGeometry(200, 200, 400, 400)

        layout = QVBoxLayout()
        self.setLayout(layout)

        self.start_date_edit = QDateEdit()
        self.start_date_edit.setDate(QDate.currentDate())
        layout.addWidget(QLabel("Начальная дата"))
        layout.addWidget(self.start_date_edit)

        self.end_date_edit = QDateEdit()
        self.end_date_edit.setDate(QDate.currentDate())
        layout.addWidget(QLabel("Конечная дата"))
        layout.addWidget(self.end_date_edit)

        self.employee_list = QListWidget()
        self.employee_list.setSelectionMode(QListWidget.SelectionMode.MultiSelection)
        layout.addWidget(QLabel("Выберите сотрудников"))
        layout.addWidget(self.employee_list)

        self.load_employees()

        self.generate_pdf_button = QPushButton("Сохранить как PDF")
        self.generate_pdf_button.clicked.connect(self.generate_pdf_report)
        layout.addWidget(self.generate_pdf_button)

        self.generate_excel_button = QPushButton("Сохранить как Excel")
        self.generate_excel_button.clicked.connect(self.generate_excel_report)
        layout.addWidget(self.generate_excel_button)

    def load_employees(self):
        employees = self.db.get_all_employees()
        for employee in employees:
            self.employee_list.addItem(f"{employee['id']} - {employee['full_name']}")

    def generate_pdf_report(self):
        selected_items = self.employee_list.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "Ошибка", "Выберите хотя бы одного сотрудника")
            return

        start_date = self.start_date_edit.date().toString("yyyy-MM-dd")
        end_date = self.end_date_edit.date().toString("yyyy-MM-dd")

        user_ids = [int(item.text().split(" - ")[0]) for item in selected_items]

        report_data = {}
        for user_id in user_ids:
            work_time = self.db.get_work_time_for_period(user_id, start_date, end_date)
            report_data[user_id] = work_time

        file_path, _ = QFileDialog.getSaveFileName(self, "Сохранить отчет как PDF", "", "PDF Files (*.pdf)")
        if not file_path:
            return

        c = canvas.Canvas(file_path, pagesize=letter)
        c.setFont("Helvetica", 12)
        c.drawString(100, 800, f"Отчет с {start_date} по {end_date}")
        y = 750
        for user_id, records in report_data.items():
            employee_name = next(item.text().split(" - ")[1] for item in selected_items if str(user_id) in item.text())
            c.drawString(50, y, f"Сотрудник: {employee_name}")
            y -= 20
            for record in records:
                c.drawString(70, y, f"{record['date']}: {record['hours']} часов")
                y -= 20
            y -= 10
        c.save()

        self.db.save_report(user_ids, start_date, end_date, report_data)
        QMessageBox.information(self, "Успех", f"Отчет сохранен как {file_path}")

    def generate_excel_report(self):
        selected_items = self.employee_list.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "Ошибка", "Выберите хотя бы одного сотрудника")
            return

        start_date = self.start_date_edit.date().toString("yyyy-MM-dd")
        end_date = self.end_date_edit.date().toString("yyyy-MM-dd")

        user_ids = [int(item.text().split(" - ")[0]) for item in selected_items]

        report_data = {}
        for user_id in user_ids:
            work_time = self.db.get_work_time_for_period(user_id, start_date, end_date)
            report_data[user_id] = work_time

        file_path, _ = QFileDialog.getSaveFileName(self, "Сохранить отчет как Excel", "", "Excel Files (*.xlsx)")
        if not file_path:
            return

        workbook = xlsxwriter.Workbook(file_path)
        worksheet = workbook.add_worksheet()

        worksheet.write(0, 0, "Сотрудник")
        worksheet.write(0, 1, "Дата")
        worksheet.write(0, 2, "Часы")

        row = 1
        for user_id, records in report_data.items():
            employee_name = next(item.text().split(" - ")[1] for item in selected_items if str(user_id) in item.text())
            for record in records:
                worksheet.write(row, 0, employee_name)
                worksheet.write(row, 1, record["date"].strftime("%Y-%m-%d"))
                worksheet.write(row, 2, record["hours"])
                row += 1

        workbook.close()

        self.db.save_report(user_ids, start_date, end_date, report_data)
        QMessageBox.information(self, "Успех", f"Отчет сохранен как {file_path}")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    login_window = LoginWindow()
    login_window.show()
    sys.exit(app.exec())

