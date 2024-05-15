import country_converter as coco
import csv


# currently supports ~2010-2023
# team emojis
team_emoji_ids = {
    "Red Bull":1081767515790770247,
    "red_bull":1081767515790770247,
    "Red Bull Racing":1081767515790770247,
    "Mercedes":1081767514620571749,
    "mercedes":1081767514620571749,
    "Ferrari":1081767510019411978,
    "ferrari":1081767510019411978,
    "McLaren":1081767512733126736,
    "mclaren":1081767512733126736,
    "Alpine":1138094801150029824,
    "alpine":1138094801150029824,
    "Alpine F1 Team":1138094801150029824,
    "Renault":1081819628906496063,
    "Lotus F1":1081821034564558878,
    "Lotus":1081821034564558878,
    "Team Lotus":1081821034564558878,
    "Aston Martin":1081767508287176734,
    "aston_martin":1081767508287176734,
    "Alfa Romeo":1081767504617148417,
    "Alfa Romeo Racing":1081767504617148417,
    "alfa":1081767504617148417,
    "Sauber":1081820021497544704,
    "AlphaTauri":1081767505539903508,
    "alphatauri":1081767505539903508,
    "Toro Rosso":1081767505539903508,
    "Force India":1081818541684162570,
    "Racing Point":1081818443252244562,
    "Williams":1081767613283176579,
    "williams":1081767613283176579,
    "Haas F1 Team":1081767511424520313,
    "haas":1081767511424520313,
    "Manor Marussia":1081822299671498792,
    "Marussia":1081822299671498792,
    "Caterham":1122921348960878622,
    "HRT":1122923506842214420,
    "Virgin":1122924331895377930,
    "RB F1 Team":1213567098631229440
}

tire_emoji_ids = {
    "HYPERSOFT":1129560960508624896,
    "ULTRASOFT":1129560966812684308,
    "SUPERSOFT":1129560965273354402,
    "SOFT":1129191871260921919,
    "MEDIUM":1129191869855846410,
    "HARD":1129191868970844300,
    "INTERMEDIATE":1129192509835313154,
    "WET":1129192511689216142,
    "SUPERHARD":1129560963805356032
}

tire_emoji_ids_2018 = {
    "HYPERSOFT":1129560960508624896,
    "ULTRASOFT":1129560966812684308,
    "SUPERSOFT":1129560965273354402,
    "SOFT":1129560962840670301,
    "MEDIUM":1129560961649492078,
    "HARD":1129560958826721330,
    "SUPERHARD":1129560963805356032
}

def get_emoji(country_name):
    emoji = ":flag_" + \
                (coco.convert(
                    names=country_name, to='ISO2')).lower()+":"
    return emoji

def nation_dictionary():
    csv_filename = "lib/nation.csv"
    with open(csv_filename, encoding='utf-8') as csvreader:
        reader = csv.reader(csvreader)
        next(reader)
        nation_dict = {}
        for row in reader:
            if row[0] in nation_dict:
                nation_dict[row[0]].append(row[1])
            else:
                nation_dict[row[0]] = [row[1]]
    return nation_dict