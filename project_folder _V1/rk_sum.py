import requests
import time
import logging


logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

def get_advert_ids(api_key):
    url = 'https://advert-api.wildberries.ru/adv/v1/promotion/count'
    headers = {
        'accept': 'application/json',
        'Authorization': api_key
    }

    try:
        # Отправляем GET-запрос
        response = requests.get(url, headers=headers)

        # Проверяем успешность запроса
        if response.status_code == 200:
            data = response.json()
            advert_ids = []

            # Проверяем наличие ключа 'adverts' в ответе
            if 'adverts' in data:
                for advert in data['adverts']:
                    if 'advert_list' in advert:
                        for item in advert['advert_list']:
                            # Сохраняем advertId в список
                            advert_ids.append(item['advertId'])

            return advert_ids

        else:
            print(f"Ошибка: {response.status_code} - {response.text}")
            return []

    except Exception as e:
        print(f"Произошла ошибка: {e}")
        return []

# Пример использования функции
advert_ids = get_advert_ids(api_key)
logger.info(f"Состояние пользователя {advert_ids}")
