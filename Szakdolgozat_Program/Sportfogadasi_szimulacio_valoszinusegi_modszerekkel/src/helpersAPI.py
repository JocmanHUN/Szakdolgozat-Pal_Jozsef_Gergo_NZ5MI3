import json,os

def write_to_file(data, filename):
    """
    Adatok mentése JSON formátumban egy fájlba.
    :param data: A mentendő adatok (list vagy dict).
    :param filename: A fájl neve, amibe menteni szeretnénk.
    """
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
    except IOError as e:
        print(f"Nem sikerült a fájlba írás: {e}")

def read_from_file(filename):
    """
    Adatok beolvasása fájlból.
    :param filename: A fájl neve, amit be kell olvasni.
    :return: Az adatok listája vagy üres lista, ha a fájl nem található.
    """
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data
    except FileNotFoundError:
        return []  # Üres listával tér vissza, ha a fájl nem létezik

def clear_file(filename):
    """
    Törli a fájl tartalmát, ha létezik és nem üres.
    :param filename: A fájl neve.
    """
    try:
        if os.path.exists(filename):
            os.remove(filename)  # Teljes törlés
            print(f"{filename} fájl törölve.")
        else:
            print(f"{filename} fájl nem létezett, nincs mit törölni.")
    except IOError as e:
        print(f"Nem sikerült törölni a fájlt: {e}")
