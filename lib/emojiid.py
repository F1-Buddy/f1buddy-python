import country_converter as coco
import csv


# currently supports ~2010-2023
# team emojis
team_emoji_ids = {
    "Red Bull Racing":1081767515790770247,
    "Mercedes":1081767514620571749,
    "Ferrari":1081767510019411978,
    "McLaren":1081767512733126736,
    "Alpine":1081767507209224192,
    "Renault":1081819628906496063,
    "Lotus F1":1081821034564558878,
    "Lotus":1081821034564558878,
    "Team Lotus":1081821034564558878,
    "Aston Martin":1081767508287176734,
    "Alfa Romeo":1081767504617148417,
    "Sauber":1081820021497544704,
    "AlphaTauri":1081767505539903508,
    "Toro Rosso":1081767505539903508,
    "Force India":1081818541684162570,
    "Racing Point":1081818443252244562,
    "Williams":1081767613283176579,
    "Haas F1 Team":1081767511424520313,
    "Manor Marussia":1081822299671498792,
    "Marussia":1081822299671498792
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