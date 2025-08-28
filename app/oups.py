import json

# Lire le fichier d'origine
with open("consommation_cafe.json", "r", encoding="utf-8") as f:
    ancienne_structure = json.load(f)

# Nouvelle structure souhaitée
nouvelle_structure = {"personnes": []}

for identifiant, donnees in ancienne_structure.items():
    personne = {
        "nom": donnees["nom"],
        "prenom": donnees["prenom"],
        "cafes": donnees["cafes"],
        "dette": donnees["dette"]
    }
    nouvelle_structure["personnes"].append(personne)

# Sauvegarder la nouvelle structure dans conso.json
with open("conso.json", "w", encoding="utf-8") as f:
    json.dump(nouvelle_structure, f, indent=2, ensure_ascii=False)
