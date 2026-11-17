# Gestion de bibliothèque — Python MVC

Application console de prêt de livres organisée en architecture **Modèle–Vue–Contrôleur (MVC)**. Elle utilise SQLite, inclus dans Python : aucune bibliothèque externe n'est nécessaire.

## Démarrer

Depuis la racine du projet :

```powershell
python main.py
```

Au premier lancement, l'application crée le catalogue de **161 livres** (deux exemplaires par titre) et ses deux bases dans le dossier `bibliothèque/` :

- `bibliotheque.db` : catalogue, membres et emprunts;
- `historique.db` : inscriptions, connexions, emprunts et retours.



## Architecture

```text
GESTION_BIBLIO/
├── main.py
├── requirements.txt
├── controllers/
│   └── bibliotheque_controller.py
├── models/
│   ├── bibliotheque_model.py
│   └── catalogue.py
├── views/
│   └── console_view.py
└── bibliothèque/             # bases de données uniquement
    ├── bibliotheque.db       # créée au premier lancement
    └── historique.db         # créée au premier lancement
```

- **Modèle** (`models/`) : données, règles de prêt et accès SQLite.
- **Vue** (`views/`) : menus, saisies et reçu imprimé à l'écran.
- **Contrôleur** (`controllers/`) : coordonne la vue et les modèles, puis inscrit les opérations dans l'historique.
- **Point d'entrée** (`main.py`) : initialise les modèles et lance la vue.

## Parcours membre

1. À chaque ouverture, le membre saisit son nom et son numero de téléphone.
2. Le programme retrouve sa fiche si le nom et le numéro correspondent; sinon, il crée une fiche et attribue un matricule de type `BIB-2026-0001`.
3. Un numéro ne peut appartenir qu'à une seule fiche membre; espaces et tirets sont ignorés pour contrôler les doublons.
4. Après un emprunt, un reçu affiche le numéro d'emprunt, le membre, le matricule, le téléphone, le titre, l'auteur, la date de prêt et la date limite de retour.
5. Le membre peut consulter ses prêts actifs, rendre un livre et voir les mouvements récents.

## Règles de prêt

- Durée d'un prêt : 21 jours.
- Limite : cinq emprunts actifs par membre.
- Un exemplaire n'est prêté que s'il est disponible.
- Un membre en retard ne peut pas emprunter un autre livre avant le retour de son livre en retard.
- Le retour augmente le nombre d'exemplaires disponibles et clôt l'emprunt.

`requirements.txt` est fourni pour documenter les dépendances : le projet n'en a pas d'externe. Le catalogue de démonstration est défini dans `models/catalogue.py`.
