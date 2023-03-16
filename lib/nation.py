import csv

def nation_dictionary():
    csv_filename = "nation.csv"
    with open(csv_filename, encoding='utf-8') as csvreader:
        reader = csv.reader(csvreader)
        next(reader)
        nation_dict = {}
        for row in reader:
            if row[0] in nation_dict:
                nation_dict[row[0]].append(row[1])
            else:
                nation_dict[row[0]] = [row[1]]
        print(nation_dict)