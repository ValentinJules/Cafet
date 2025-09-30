from flask import Flask, render_template, request, redirect, url_for
import json
import os
from datetime import datetime
from flask import send_file
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
import io
from reportlab.lib.utils import ImageReader

app = Flask(__name__)
# prix_par_cafe = 0.30


FICHIER_JSON = "./conso.json"



@app.route("/")
def index():
    # Charger les données des personnes
    donnees_conso = charger_donnees()  # conso.json
    personnes = donnees_conso["personnes"]
    
    # Charger les données de la caisse
    donnees_caisse = charger_caisse()  # caisse.json
    responsable = donnees_caisse["responsable"]
    caisse = donnees_caisse["caisse"]
    prix_cafe = donnees_caisse["prix_par_cafe"]
    
    return render_template("index.html", 
                         personnes=personnes, 
                         responsable=responsable, 
                         caisse=caisse,
                         prix_cafe=prix_cafe)


def charger_donnees():
    with open(FICHIER_JSON, "r", encoding="utf-8") as f:
        return json.load(f)

def enregistrer_donnees(donnees):
    with open(FICHIER_JSON, "w", encoding="utf-8") as f:
        json.dump(donnees, f, indent=2, ensure_ascii=False)

def charger_caisse():
    try:
        with open("caisse.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        # Fichier par défaut si inexistant
        return {
            "responsable": {"prenom": "Prénom", "nom": "Nom"},
            "caisse": 0,
            "prix_par_cafe": 0.5
        }

def enregistrer_caisse(donnees):
    with open("caisse.json", "w", encoding="utf-8") as f:
        json.dump(donnees, f, ensure_ascii=False, indent=4)

@app.route("/ajouter", methods=["GET", "POST"])
def ajouter():
    if request.method == "POST":
        prenom = request.form["prenom"].strip()
        nom = request.form["nom"].strip()
        statut = request.form["statut"]  # Récupérer le statut
        personnes = charger_donnees()["personnes"]

        # Vérifier si la personne existe déjà (nom & prénom)
        existe_deja = any(p["nom"].lower() == nom.lower() and p["prenom"].lower() == prenom.lower() for p in personnes)

        if not existe_deja:
            nouvelle_personne = {
                "nom": nom,
                "prenom": prenom,
                "statut": statut,  # Ajouter le statut
                "cafes": 0,
                "dette": 0.0
            }
            personnes.append(nouvelle_personne)
            enregistrer_donnees({"personnes": personnes})

        return redirect(url_for("index"))

    return render_template("ajouter.html")

@app.route("/supprimer", methods=["GET", "POST"])
def supprimer():
    donnees = charger_donnees()
    personnes = donnees["personnes"]

    if request.method == "POST":
        champ = request.form["personne"]
        prenom, nom = champ.split("|")

        # Supprimer la personne
        personnes = [p for p in personnes if not (
            p["nom"].lower() == nom.lower() and p["prenom"].lower() == prenom.lower()
        )]

        enregistrer_donnees({"personnes": personnes})
        return redirect(url_for("index"))

    return render_template("supprimer.html", personnes=personnes)





@app.route("/consommation", methods=["GET", "POST"])
def consommation():
    donnees_conso = charger_donnees()
    donnees_caisse = charger_caisse()
    personnes = donnees_conso["personnes"]
    prix_cafe = donnees_caisse["prix_par_cafe"]

    if request.method == "POST":
        for i, personne in enumerate(personnes):
            key = f"cafes_{i}"
            nb = request.form.get(key)
            if nb:
                try:
                    nb_cafes = int(nb)
                    if nb_cafes > 0:
                        personne["cafes"] = nb_cafes
                        
                        # Appliquer le prix réduit pour les stagiaires
                        if personne.get("statut") == "stagiaire":
                            prix_cafe = prix_par_cafe / 2
                        else:
                            prix_cafe = prix_par_cafe
                        
                        personne["dette"] += round(nb_cafes * prix_cafe, 2)
                except ValueError:
                    continue  # ignore les valeurs invalides

        enregistrer_donnees({"personnes": personnes})
        return redirect(url_for("index"))

    return render_template("consommation.html", personnes=personnes)


@app.route("/dettes")
def dettes():
    donnees = charger_donnees()
    personnes = donnees["personnes"]
    # Trier par dette décroissante
    personnes_triees = sorted(personnes, key=lambda x: x["dette"], reverse=True)
    return render_template("dettes.html", personnes=personnes_triees)



@app.route("/caisse")
def page_caisse():
    caisse = get_caisse()
    responsable = get_responsable()
    return render_template("caisse.html", caisse=caisse, responsable=responsable)

@app.route('/responsable', methods=['GET', 'POST'])
def responsable():
    donnees = charger_donnees()  # On récupère toutes les données nécessaires (dont les personnes)
    
    if request.method == 'POST':
        try:
            # On récupère la valeur du champ et on sépare prénom et nom
            prenom, nom = map(str.strip, request.form['responsable'].split('|'))
            
            # Charger le contenu actuel du fichier caisse.json
            with open('caisse.json', 'r', encoding='utf-8') as f:
                caisse_data = json.load(f)
            
            # Mettre à jour le responsable
            caisse_data['responsable'] = {'prenom': prenom, 'nom': nom}
            
            # Réécrire le fichier mis à jour
            with open('caisse.json', 'w', encoding='utf-8') as f:
                json.dump(caisse_data, f, indent=4, ensure_ascii=False)
        
        except (ValueError, KeyError) as e:
            # En cas d'erreur, on pourrait afficher un message ou logger l'erreur
            print(f"Erreur lors de la mise à jour du responsable : {e}")
        
        return redirect(url_for('index'))
    
    # En GET, on renvoie la page pour choisir un responsable
    personnes = donnees.get('personnes', [])
    return render_template('responsable.html', personnes=personnes)

@app.route("/changer_statut", methods=["GET", "POST"])
def changer_statut():
    donnees = charger_donnees()
    personnes = donnees["personnes"]

    if request.method == "POST":
        # Récupérer la personne sélectionnée et le nouveau statut
        champ_personne = request.form["personne"]
        nouveau_statut = request.form["statut"]
        
        prenom, nom = champ_personne.split("|")

        # Trouver et mettre à jour la personne
        for personne in personnes:
            if (personne["nom"].lower() == nom.lower() and 
                personne["prenom"].lower() == prenom.lower()):
                personne["statut"] = nouveau_statut
                break

        enregistrer_donnees({"personnes": personnes})
        return redirect(url_for("index"))

    return render_template("changer_statut.html", personnes=personnes)


@app.route('/payer', methods=['GET', 'POST'])
def payer():
    donnees = charger_donnees()

    if request.method == 'POST':
        prenom, nom = request.form['personne'].split('|')
        montant = float(request.form['montant'])
        moyen = request.form['moyen']

        # Mise à jour de la dette de la personne
        for p in donnees['personnes']:
            if p['prenom'] == prenom and p['nom'] == nom:
                p['dette'] -= montant
                break

        # Charger caisse.json
        with open('caisse.json', 'r') as f:
            caisse_data = json.load(f)

        if moyen == 'liquide':
            caisse_data['caisse'] += montant
        elif moyen == 'virement':
            responsable = caisse_data.get('responsable')
            if responsable:
                for p in donnees['personnes']:
                    if p['prenom'] == responsable['prenom'] and p['nom'] == responsable['nom']:
                        p['dette'] += montant
                        break

        # Enregistrer les changements
        enregistrer_donnees(donnees)
        with open('caisse.json', 'w') as f:
            json.dump(caisse_data, f, indent=4)

        return redirect(url_for('index'))

    return render_template('payer.html', personnes=donnees['personnes'])


@app.route("/exporter_pdf")
def exporter_pdf():
    data = charger_donnees()
    
    # Récupérer la liste des personnes
    personnes = data.get("personnes", [])
    
    # Filtrer celles avec une dette positive (>0)
    dettes_positives = [p for p in personnes if p["dette"] > 1 and p.get("statut") != "inactif"]

    # Création du PDF en mémoire
    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    # Titre
    p.setFont("Helvetica-Bold", 16)
    p.drawString(50, height - 50, "Liste des dettes café")
    p.setFont("Helvetica", 10)
    p.drawString(50, height - 70, f"Date d'export : {datetime.now().strftime('%d/%m/%Y %H:%M')}")

    # Dimensions du tableau
    y_start = height - 100
    line_height = 20
    col_widths = [150, 150, 100]  # Largeurs des colonnes
    col_positions = [50, 200, 350]  # Positions X des colonnes
    table_width = sum(col_widths)
    
    # En-têtes du tableau
    y = y_start
    p.setFont("Helvetica-Bold", 11)
    
    # Dessiner le cadre de l'en-tête
    p.rect(col_positions[0], y, table_width, -line_height, fill=0)
    
    # Dessiner les séparateurs de colonnes
    p.line(col_positions[1], y, col_positions[1], y - line_height)
    p.line(col_positions[2], y, col_positions[2], y - line_height)
    
    # Texte des en-têtes
    p.drawString(col_positions[0] + 5, y - 15, "Nom")
    p.drawString(col_positions[1] + 5, y - 15, "Prénom")
    p.drawString(col_positions[2] + 5, y - 15, "Dette (€)")
    
    y -= line_height

    # Données du tableau
    p.setFont("Helvetica", 10)
    for infos in sorted(dettes_positives, key=lambda x: (x["nom"], x["prenom"])):
        if y < 50:  # Nouvelle page si on arrive en bas
            p.showPage()
            y = height - 50
            # Retitre sur la nouvelle page
            p.setFont("Helvetica-Bold", 16)
            p.drawString(50, height - 50, "Liste des dettes café (suite)")
            y = height - 100
            
            # Redessiner l'en-tête du tableau
            p.setFont("Helvetica-Bold", 11)
            p.rect(col_positions[0], y, table_width, -line_height, fill=0)
            p.line(col_positions[1], y, col_positions[1], y - line_height)
            p.line(col_positions[2], y, col_positions[2], y - line_height)
            p.drawString(col_positions[0] + 5, y - 15, "Nom")
            p.drawString(col_positions[1] + 5, y - 15, "Prénom")
            p.drawString(col_positions[2] + 5, y - 15, "Dette (€)")
            y -= line_height
            p.setFont("Helvetica", 10)

        # Dessiner le cadre de la ligne
        p.rect(col_positions[0], y, table_width, -line_height, fill=0)
        
        # Dessiner les séparateurs de colonnes pour cette ligne
        p.line(col_positions[1], y, col_positions[1], y - line_height)
        p.line(col_positions[2], y, col_positions[2], y - line_height)
        
        # Contenu des cellules
        p.drawString(col_positions[0] + 5, y - 15, infos["nom"])
        p.drawString(col_positions[1] + 5, y - 15, infos["prenom"])
        p.drawRightString(col_positions[2] + col_widths[2] - 5, y - 15, f"{infos['dette']:.2f} €")
        
        y -= line_height

    # Total des dettes
    total_dettes = sum(p["dette"] for p in dettes_positives)
    y -= 10  # Espace avant le total
    
    # Ligne de séparation
    p.line(col_positions[0], y, col_positions[0] + table_width, y)
    y -= 10
    
    p.setFont("Helvetica-Bold", 11)
    p.drawString(col_positions[0], y - 15, "TOTAL DES DETTES :")
    p.drawRightString(col_positions[2] + col_widths[2] - 5, y - 15, f"{total_dettes:.2f} €")

    p.save()
    buffer.seek(0)

    return send_file(
        buffer,
        as_attachment=True,
        download_name="dettes_cafes.pdf",
        mimetype="application/pdf"
    )

@app.route('/acheter', methods=['GET', 'POST'])
def acheter():
    donnees = charger_donnees()

    if request.method == 'POST':
        try:
            quantite = float(request.form['quantite'])
            prix = float(request.form['prix'])
            paiement = request.form['paiement']

            # Charger la caisse
            with open('caisse.json', 'r', encoding='utf-8') as f:
                caisse_data = json.load(f)

            # Augmenter le stock
            caisse_data['stock'] = caisse_data.get('stock', 0) + quantite

            # Paiement liquide → caisse diminue
            if paiement == 'liquide':
                caisse_data['caisse'] -= prix

            # Chercher le responsable et diminuer sa dette
            responsable = caisse_data['responsable']
            trouve = False
            for personne in donnees.get('personnes', []):
                if personne['prenom'] == responsable['prenom'] and personne['nom'] == responsable['nom']:
                    ancienne_dette = float(personne.get('dette', 0))
                    personne['dette'] = ancienne_dette - prix
                    print(f"Dette modifiée pour {personne['prenom']} {personne['nom']} : {ancienne_dette} -> {personne['dette']}")
                    trouve = True
                    break

            if not trouve:
                print("Responsable introuvable dans donnees.json")

            # Sauvegarder
            with open('caisse.json', 'w', encoding='utf-8') as f:
                json.dump(caisse_data, f, indent=4, ensure_ascii=False)

            with open('conso.json', 'w', encoding='utf-8') as f:
                json.dump(donnees, f, indent=4, ensure_ascii=False)

            # Historique (identique à avant)
            achat = {
                "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "responsable": responsable,
                "quantite": quantite,
                "prix": prix,
                "paiement": paiement
            }

            historique_file = 'historique.json'
            if os.path.exists(historique_file):
                with open(historique_file, 'r', encoding='utf-8') as f:
                    historique = json.load(f)
            else:
                historique = []

            historique.append(achat)

            with open(historique_file, 'w', encoding='utf-8') as f:
                json.dump(historique, f, indent=4, ensure_ascii=False)

        except Exception as e:
            print(f"Erreur lors de l'achat : {e}")

        return redirect(url_for('index'))

    return render_template('acheter.html')

@app.route('/historique')
def historique():
    if os.path.exists('historique.json'):
        with open('historique.json', 'r', encoding='utf-8') as f:
            achats = json.load(f)
    else:
        achats = []

    return render_template('historique.html', achats=achats)



@app.route("/trier_liste")
def trier_liste():
    donnees = charger_donnees()
    personnes = donnees["personnes"]
    
    # Trier les personnes par nom (puis par prénom en cas d'égalité)
    personnes_triees = sorted(personnes, key=lambda x: (x["nom"].lower(), x["prenom"].lower()))
    
    # Mettre à jour les données avec la liste triée
    donnees["personnes"] = personnes_triees
    enregistrer_donnees(donnees)
    
    return redirect(url_for("index"))


@app.route("/changer_prix", methods=["GET", "POST"])
def changer_prix():
    donnees_caisse = charger_caisse()  # Charger depuis caisse.json
    
    if request.method == "POST":
        nouveau_prix = request.form.get("prix_cafe")
        
        if nouveau_prix:
            try:
                prix_float = float(nouveau_prix)
                if prix_float > 0:
                    donnees_caisse["prix_par_cafe"] = prix_float
                    enregistrer_caisse(donnees_caisse)  # Sauvegarder dans caisse.json
                    return redirect(url_for("index"))
                else:
                    return render_template("changer_prix.html", error="Le prix doit être supérieur à 0")
            except ValueError:
                return render_template("changer_prix.html", error="Veuillez entrer un prix valide")
    
    return render_template("changer_prix.html", prix_actuel=donnees_caisse["prix_par_cafe"])

@app.route("/exporter_grille_pdf")
def exporter_grille_pdf():
    data = charger_donnees()
    personnes = data.get("personnes", [])
    
    # Filtrer les personnes actives
    personnes_actives = [p for p in personnes if p.get("statut") != "inactif"]
    personnes_triees = sorted(personnes_actives, key=lambda x: x["nom"])
    
    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    
    # Configuration
    y = height - 50
    line_height = 15
    nom_col_width = 80
    prenom_col_width = 80
    case_width = 15
    nb_cases_ligne = 20  # 20 cases par ligne
    
    # Titre
    p.setFont("Helvetica-Bold", 16)
    p.drawString(50, y, "Grille des consommations de café")
    p.setFont("Helvetica", 10)
    p.drawString(50, y - 20, f"Export du {datetime.now().strftime('%d/%m/%Y')}")
    p.drawString(50, y - 35, "Prix: 0,30€ (0,15€ pour stagiaires)")
    
    y -= 60
    
    # En-têtes des colonnes
    p.setFont("Helvetica-Bold", 10)
    p.drawString(50, y, "Nom")
    p.drawString(140, y, "Prénom")
    p.drawString(230, y, "Cases à cocher")
    
    y -= 25
    
    # Ligne de séparation
    p.line(50, y, 50 + nom_col_width + prenom_col_width + (nb_cases_ligne * case_width), y)
    y -= 10
    
    # Données des personnes
    p.setFont("Helvetica", 9)
    
    for personne in personnes_triees:
        # Vérifier si on doit changer de page
        if y < 80:  # Plus d'espace nécessaire pour 2 lignes
            p.showPage()
            y = height - 50
            
            # Redessiner les en-têtes
            p.setFont("Helvetica-Bold", 10)
            p.drawString(50, y, "Nom")
            p.drawString(140, y, "Prénom")
            p.drawString(230, y, "Cases à cocher")
            
            y -= 25
            p.line(50, y, 50 + nom_col_width + prenom_col_width + (nb_cases_ligne * case_width), y)
            y -= 10
            p.setFont("Helvetica", 9)
        
        # Ligne 1 - Nom + première ligne de cases
        p.drawString(55, y - 10, personne["nom"])
        
        # Cases de la ligne 1
        for i in range(nb_cases_ligne):
            x_pos = 230 + (i * case_width)
            p.rect(x_pos, y - 12, case_width, line_height)
        
        y -= line_height
        
        # Ligne 2 - Prénom + deuxième ligne de cases
        p.drawString(55, y - 10, personne["prenom"])
        
        # Cases de la ligne 2
        for i in range(nb_cases_ligne):
            x_pos = 230 + (i * case_width)
            p.rect(x_pos, y - 12, case_width, line_height)
        
        y -= line_height + 10  # Espacement entre les personnes
    

    
    p.save()
    buffer.seek(0)
    
    return send_file(
        buffer,
        as_attachment=True,
        download_name=f"grille_cafe_{datetime.now().strftime('%d_%m_%Y')}.pdf",
        mimetype="application/pdf"
    )





if __name__ == "__main__":
    app.run(debug=True)
