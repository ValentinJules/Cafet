import os
import json

responsable_cafet_file = "responsable.json"
caisse_file = "caisse.json"

# Initialiser responsable si le fichier n'existe pas
def init_responsable():
    if not os.path.exists(responsable_cafet_file):
        with open(responsable_cafet_file, 'w') as f:
            json.dump({"nom": "Jules", "prenom": "Valentin", "dette": 0.0}, f)

def get_responsable():
    with open(responsable_cafet_file) as f:
        return json.load(f)

def set_responsable(nom, prenom):
    with open(responsable_cafet_file, 'w') as f:
        json.dump({"nom": nom, "prenom": prenom, "dette": 0.0}, f)

# Initialiser la caisse

def init_caisse():
    if not os.path.exists(caisse_file):
        with open(caisse_file, 'w') as f:
            json.dump({"caisse": 40.0}, f)

def get_caisse():
    with open(caisse_file) as f:
        return json.load(f)["caisse"]

def update_caisse(montant):
    montant_total = get_caisse() + montant
    with open(caisse_file, 'w') as f:
        json.dump({"caisse": montant_total}, f)


init_responsable()
init_caisse()
