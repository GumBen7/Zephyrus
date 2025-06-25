from models import City

G_PROJECT_ID = 'silicon-clock-463914-i2'
DISTANCES_KM = [10, 20, 30, 50, 100, 150, 200]
BEARINGS_DEG = [0, 45, 90, 135, 180, 225, 270, 315]
BEARINGS = {
    0: "Север",
    45: "Северо-Восток",
    90: "Восток",
    135: "Юго-Восток",
    180: "Юг",
    225: "Юго-Запад",
    270: "Запад",
    315: "Северо-Запад"
}
YEARS_TO_ANALYZE = [2019, 2020, 2021, 2022, 2023, 2024]
MONTH_TO_ANALYZE = 2
EARTH_RADIUS_KM = 6371
GEE_NO2_COLLECTION = "COPERNICUS/S5P/OFFL/L3_NO2"
GEE_COLLECTION_SCALE = 1113.2
MOL_PER_M2_TO_UMOL_PER_M2 = 10 ** 6
EXPORTS_FOLDER = "exports"
CITIES = {
    "moscow": City(id="moscow", name="Москва", coordinates=(52.033635, 113.501049), routes=[]),
    "saint_petersburg": City(id="saint_petersburg", name="Санкт-Петербург", coordinates=(59.9343, 30.3351), routes=[]),
    "novosibirsk": City(id="novosibirsk", name="Новосибирск", coordinates=(55.030204, 82.920430), routes=[]),
    "ekaterinburg": City(id="ekaterinburg", name="Екатеринбург", coordinates=(56.8380, 60.5975), routes=[]),
    "kazan": City(id="kazan", name="Казань", coordinates=(55.7961, 49.1064), routes=[]),
    "nizhny_novgorod": City(id="nizhny_novgorod", name="Нижний Новгород", coordinates=(56.3269, 44.0059), routes=[]),
    "chelyabinsk": City(id="chelyabinsk", name="Челябинск", coordinates=(55.1644, 61.4025), routes=[]),
    "samara": City(id="samara", name="Самара", coordinates=(53.1959, 50.1002), routes=[]),
    "omsk": City(id="omsk", name="Омск", coordinates=(54.9894, 73.3686), routes=[]),
    "rostov_on_don": City(id="rostov_on_don", name="Ростов-на-Дону", coordinates=(47.2221, 39.7188), routes=[]),
    "ufa": City(id="ufa", name="Уфа", coordinates=(54.7351, 55.9587), routes=[]),
    "krasnoyarsk": City(id="krasnoyarsk", name="Красноярск", coordinates=(56.0105, 92.8526), routes=[]),
    "voronezh": City(id="voronezh", name="Воронеж", coordinates=(51.6615, 39.2003), routes=[]),
    "perm": City(id="perm", name="Пермь", coordinates=(58.0105, 56.2502), routes=[]),
    "volgograd": City(id="volgograd", name="Волгоград", coordinates=(48.7071, 44.5169), routes=[]),
    "chita": City(id="chita", name="Чита", coordinates=(52.0336, 113.5010), routes=[])
}
MONTHS = {
    1: "Январь", 2: "Февраль", 3: "Март", 4: "Апрель",
    5: "Май", 6: "Июнь", 7: "Июль", 8: "Август",
    9: "Сентябрь", 10: "Октябрь", 11: "Ноябрь", 12: "Декабрь"
}
