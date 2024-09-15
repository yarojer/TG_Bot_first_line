import requests
import pandas as pd
import logging
import os
from aiogram import Bot, types
from datetime import datetime, timedelta
from calculator import calculate_all_combinations, generate_summary_data
import time


# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('logfile.log')
    ]
)
logger = logging.getLogger(__name__)

# Маппинг названий столбцов для переименования
column_mapping = {
        'realizationreport_id': 'Номер отчёта',
        'date_from': 'Дата начала отчётного периода',
        'date_to': 'Дата конца отчётного периода',
        'create_dt': 'Дата формирования отчёта',
        'currency_name': 'Валюта отчёта',
        'suppliercontract_code': 'Договор',
        'gi_id': 'Номер поставки',
        'subject_name': 'Предмет',
        'nm_id': 'Артикул WB',
        'brand_name': 'Бренд',
        'sa_name': 'Артикул продавца',
        'ts_name': 'Размер',
        'barcode': 'Баркод',
        'doc_type_name': 'Тип документа',
        'quantity': 'Количество',
        'retail_price': 'Цена розничная',
        'retail_amount': 'Сумма продаж (возвратов)',
        'sale_percent': 'Согласованная скидка',
        'commission_percent': 'Процент комиссии',
        'office_name': 'Склад',
        'supplier_oper_name': 'Обоснование для оплаты',
        'order_dt': 'Дата заказа покупателем',
        'sale_dt': 'Дата продажи',
        'rr_dt': 'Дата операции',
        'shk_id': 'Штрих-код',
        'retail_price_withdisc_rub': 'Цена розничная с учетом согласованной скидки',
        'delivery_amount': 'Количество доставок',
        'return_amount': 'Количество возвратов',
        'delivery_rub': 'Услуги по доставке товара покупателю',
        'gi_box_type_name': 'Тип коробов',
        'product_discount_for_report': 'Согласованный продуктовый дисконт',
        'supplier_promo': 'Промокод',
        'ppvz_spp_prc': 'Скидка постоянного покупателя',
        'ppvz_kvw_prc_base': 'Размер кВВ без НДС, % базовый',
        'ppvz_kvw_prc': 'Итоговый кВВ без НДС, %',
        'sup_rating_prc_up': 'Размер снижения кВВ из-за рейтинга',
        'is_kgvp_v2	': 'Размер снижения кВВ из-за акции',
        'ppvz_sales_commission': 'Вознаграждение с продаж до вычета услуг поверенного, без НДС',
        'ppvz_for_pay': 'К перечислению Продавцу за реализованный Товар',
        'ppvz_reward': 'Возмещение за выдачу и возврат товаров на ПВЗ',
        'acquiring_fee': 'Возмещение издержек по эквайрингу.Издержки WB за услуги эквайринга: вычитаются из вознаграждения WB и не влияют на доход продавца.',
        'acquiring_percent': 'Размер комиссии за эквайринг без НДС, %',
        'acquiring_bank': 'Наименование банка-эквайера',
        'ppvz_vw': 'Вознаграждение WB без НДС',
        'ppvz_vw_nds': 'НДС с вознаграждения WB',
        'ppvz_office_id': 'Номер офиса',
        'ppvz_office_name': 'Наименование офиса доставки',
        'ppvz_supplier_id': 'Номер партнера',
        'ppvz_supplier_name': 'Партнер',
        'ppvz_inn': 'ИНН партнера',
        'declaration_number': 'Номер таможенной декларации',
        'bonus_type_name': 'Обоснование штрафов и доплат.',
        'sticker_id': 'Цифровое значение стикера, который клеится на товар в процессе сборки заказа по схеме "Маркетплейс"',
        'site_country': 'Страна продажи',
        'penalty': 'Общая сумма штрафов',
        'additional_payment': 'Доплаты',
        'rebill_logistic_cost': 'Возмещение издержек по перевозке',
        'rebill_logistic_org': 'Организатор перевозки',
        'storage_fee': 'Стоимость хранения',
        'deduction': 'Прочие удержания/выплаты',
        'acceptance': 'Стоимость платной приёмки'
    }

# Функция для получения данных через API с расширением дат
def fetch_data_from_api(user_key, start_date, end_date, user_id, timestamp, limit=100000):
    """
    Функция для запроса данных с расширением периода запроса и сохранения в Excel.
    """
    start_date_obj = datetime.strptime(start_date, '%d.%m.%Y')
    end_date_obj = datetime.strptime(end_date, '%d.%m.%Y')

    extended_start_date = start_date_obj - timedelta(days=14)
    extended_end_date = end_date_obj + timedelta(days=30)

    date_from = extended_start_date.strftime('%Y-%m-%d')
    date_to = extended_end_date.strftime('%Y-%m-%d')

    logger.info(f"Запрашиваем данные с {date_from} по {date_to} (расширение периода на 14 дней до и 30 дней после).")

    rrdid = 0
    all_data = []
    while True:
        url = f"https://statistics-api.wildberries.ru/api/v5/supplier/reportDetailByPeriod?dateFrom={date_from}&limit={limit}&dateTo={date_to}&rrdid={rrdid}"
        headers = {
            "accept": "application/json",
            "Authorization": user_key
        }
        logger.info(f"Отправка запроса к API: {url} с заголовками: {headers}")

        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            if not data:
                break
            all_data.extend(data)
            rrdid = data[-1]["rrd_id"]
        else:
            logger.error(f"Ошибка получения данных: {response.status_code}, Ответ: {response.text}")
            break
    
    # Преобразование данных в DataFrame
    df = pd.DataFrame(all_data)

    # Переименование столбцов и сохранение всех данных в Excel
    df = df.rename(columns=column_mapping)
    save_raw_data_to_excel(df, user_id, date_from, date_to)

    # Преобразование столбцов для соответствия с calculator.py
    df = transform_columns(df)

    # Выполнение расчетов и сохранение итогового отчета
    generate_and_save_report(df, start_date, end_date, user_id)

    return df

def save_raw_data_to_excel(df, user_id, date_from, date_to):
    """
    Сохраняет сырые данные из API в Excel файл в директорию results/{user_id}/.
    :param df: DataFrame с данными для сохранения.
    :param user_id: Идентификатор пользователя.
    :param date_from: Дата начала периода в формате 'ГГГГ-ММ-ДД'.
    :param date_to: Дата конца периода в формате 'ГГГГ-ММ-ДД'.
    """
    # Создание директории для пользователя, если не существует
    results_folder = f"results/{user_id}"
    os.makedirs(results_folder, exist_ok=True)

    # Создание уникального имени файла на основе времени запроса
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    file_name = f"Excel_Api_{date_from}_{date_to}_{timestamp}.xlsx"
    file_path = os.path.join(results_folder, file_name)

    # Сохранение DataFrame в Excel файл
    try:
        df.to_excel(file_path, index=False)
        logger.info(f"Все данные успешно сохранены в файл: {file_path}")
    except Exception as e:
        logger.error(f"Ошибка при сохранении файла Excel: {e}")

# Обработка данных и расчет на основе полученных данных из API
def process_data(df, start_date, end_date, brand_name=None):
    """
    Выполняет обработку данных и расчеты по заданным параметрам.
    :param df: DataFrame с данными.
    :param start_date: Начальная дата анализа.
    :param end_date: Конечная дата анализа.
    :param brand_name: Название бренда (опционально).
    :return: DataFrame с результатами расчетов.
    """
    # Фильтрация данных по бренду, если указан brand_name
    if brand_name:
        logger.info(f"Фильтрация данных по бренду: {brand_name}")
        df = df[df['Бренд'].str.lower() == brand_name.lower()]

    # Применяем логику расчетов из calculator.py
    result = calculate_all_combinations(df, start_date, end_date, brand_name=brand_name)
    return result

# Пример функции, где обрабатываются даты
def generate_and_save_report(df, start_date, end_date, user_id, brand_name=None):
    logger.info("Начало генерации и сохранения отчета.")

    # Преобразуем начальную и конечную даты с учетом всего дня
    start_date = pd.to_datetime(start_date, dayfirst=True).tz_localize(None)
    end_date = pd.to_datetime(end_date, dayfirst=True).tz_localize(None) + timedelta(hours=23, minutes=59, seconds=59)

    try:
        logger.info("Выполняем расчеты через calculate_all_combinations.")
        # Передаем brand_name в process_data, если он указан
        result = process_data(df, start_date, end_date, brand_name)
    except Exception as e:
        logger.error(f"Ошибка при выполнении расчетов: {e}")
        raise

    try:
        logger.info("Генерация сводных данных.")
        summary_df = generate_summary_data(result, start_date, end_date)
    except Exception as e:
        logger.error(f"Ошибка при генерации сводных данных: {e}")
        raise

    # Сохранение отчета и получение имени файла
    filename = save_report_to_excel(result, summary_df, start_date, end_date, user_id)
    return filename  # Возвращаем имя файла для дальнейшего использования


def save_report_to_excel(processed_df, summary_df, start_date, end_date, user_id):
    results_folder = f"results/{user_id}"
    os.makedirs(results_folder, exist_ok=True)
    
    # Форматирование дат в строковом формате для имени файла
    start_date_str = start_date.strftime('%Y-%m-%d')
    end_date_str = end_date.strftime('%Y-%m-%d')
    
    # Добавление уникального номера на основе времени запроса
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = os.path.join(results_folder, f"итоговый_отчет_API_{start_date_str}_{end_date_str}_{timestamp}.xlsx")

    logger.info(f"Начало сохранения итогового файла Excel в {filename}.")

    # Проверка на существование файла и его удаление перед записью
    if os.path.exists(filename):
        logger.info(f"Файл {filename} существует. Попытка удаления перед сохранением нового.")
        for attempt in range(6):
            try:
                os.remove(filename)
                logger.info(f"Старый файл {filename} успешно удален перед сохранением нового.")
                break
            except PermissionError as e:
                logger.error(f"Ошибка при удалении существующего файла: {e}. Попытка {attempt + 1} из 6. Ожидание 10 секунд.")
                time.sleep(10)
        else:
            logger.error(f"Не удалось удалить файл {filename} после шести попыток.")
            raise PermissionError(f"Не удалось удалить файл {filename} после шести попыток.")

    try:
        logger.info("Начало записи данных в Excel файл.")
        with pd.ExcelWriter(filename, engine='xlsxwriter') as writer:
            summary_df.to_excel(writer, sheet_name="Итоговые данные", index=False, header=False)
            logger.info("'Итоговые данные' записаны успешно.")
            
            processed_df.to_excel(writer, sheet_name="Общие данные", index=False)
            logger.info("'Общие данные' записаны успешно.")
        
        logger.info(f"Файл {filename} успешно сохранен.")
        return filename  # Добавляем возврат полного пути к файлу

    except PermissionError as e:
        logger.error(f"Ошибка при сохранении файла Excel: {e}. Убедитесь, что файл не открыт в других приложениях.")
        raise
    except Exception as e:
        logger.error(f"Ошибка при сохранении файла Excel: {e}")
        raise




def transform_columns(df):
    """
    Преобразует столбцы DataFrame, полученного от API, в формат, используемый в calculator.py.
    :param df: DataFrame с оригинальными данными.
    :return: DataFrame с переименованными столбцами.
    """
    # Переименование столбцов
    df = df.rename(columns=column_mapping)
    
    # Преобразование дат к единому формату без временной зоны
    df['Дата заказа покупателем'] = pd.to_datetime(df['Дата заказа покупателем'], errors='coerce').dt.tz_localize(None)
    df['Дата продажи'] = pd.to_datetime(df['Дата продажи'], errors='coerce').dt.tz_localize(None)
    df['Дата операции'] = pd.to_datetime(df['Дата операции'], errors='coerce').dt.tz_localize(None)

    return df
