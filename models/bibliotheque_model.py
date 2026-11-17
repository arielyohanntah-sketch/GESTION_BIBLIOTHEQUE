"""Modèle métier et dépôt SQLite de la bibliothèque."""

import sqlite3
import re
from contextlib import contextmanager
from datetime import date, timedelta
from pathlib import Path
from collections.abc import Iterator

from .catalogue import LIVRES

RACINE = Path(__file__).resolve().parent.parent
DOSSIER_BASES = RACINE / "bibliothèque"
BASE_BIBLIOTHEQUE = DOSSIER_BASES / "bibliotheque.db"
BASE_HISTORIQUE = DOSSIER_BASES / "historique.db"
DUREE_PRET_JOURS = 21
MAX_PRETS_ACTIFS = 5


class BibliothequeModel:
    """Gère les livres, les membres et les emprunts persistants."""

    def __init__(self, chemin: Path = BASE_BIBLIOTHEQUE) -> None:
        self.chemin = chemin
        self.chemin.parent.mkdir(parents=True, exist_ok=True)

    @contextmanager
    def connexion(self) -> Iterator[sqlite3.Connection]:
        db = sqlite3.connect(self.chemin)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys = ON")
        try:
            yield db
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    def initialiser(self) -> None:
        with self.connexion() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS livres (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    titre TEXT NOT NULL, auteur TEXT NOT NULL, categorie TEXT NOT NULL,
                    annee INTEGER NOT NULL, exemplaires INTEGER NOT NULL CHECK(exemplaires > 0),
                    disponibles INTEGER NOT NULL CHECK(disponibles >= 0 AND disponibles <= exemplaires)
                );
                CREATE TABLE IF NOT EXISTS membres (
                    matricule TEXT PRIMARY KEY, nom TEXT NOT NULL, telephone TEXT NOT NULL,
                    telephone_normalise TEXT UNIQUE,
                    cree_le TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS emprunts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    livre_id INTEGER NOT NULL REFERENCES livres(id),
                    matricule TEXT NOT NULL REFERENCES membres(matricule),
                    emprunte_le TEXT NOT NULL, a_rendre_le TEXT NOT NULL, rendu_le TEXT,
                    statut TEXT NOT NULL DEFAULT 'En cours'
                );
                CREATE INDEX IF NOT EXISTS idx_livres_recherche ON livres(titre, auteur, categorie);
                CREATE INDEX IF NOT EXISTS idx_emprunts_membre ON emprunts(matricule, rendu_le);
            """)
            colonnes_membres = {ligne[1] for ligne in db.execute("PRAGMA table_info(membres)")}
            if "telephone_normalise" not in colonnes_membres:
                db.execute("ALTER TABLE membres ADD COLUMN telephone_normalise TEXT")
            for membre in db.execute("SELECT matricule, telephone FROM membres WHERE telephone_normalise IS NULL"):
                normalise = re.sub(r"\D", "", membre["telephone"])
                db.execute("UPDATE membres SET telephone_normalise=? WHERE matricule=?",
                           (normalise, membre["matricule"]))
            doublons = db.execute("""
                SELECT telephone_normalise, COUNT(*) AS nombre
                FROM membres GROUP BY telephone_normalise HAVING COUNT(*) > 1
            """).fetchone()
            if doublons:
                raise ValueError(
                    "La base contient déjà plusieurs membres avec le même numéro. "
                    "Corrigez ces fiches avant de démarrer l'application."
                )
            db.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_membres_telephone_unique "
                       "ON membres(telephone_normalise)")
            if db.execute("SELECT COUNT(*) FROM livres").fetchone()[0] == 0:
                db.executemany(
                    "INSERT INTO livres(titre,auteur,categorie,annee,exemplaires,disponibles) VALUES(?,?,?,?,?,?)",
                    [(t, a, c, y, 2, 2) for t, a, c, y in LIVRES],
                )

    def identifier_ou_creer_membre(self, nom: str, telephone: str) -> tuple[sqlite3.Row, bool]:
        nom, telephone = nom.strip(), telephone.strip()
        if len(nom) < 2:
            raise ValueError("Le nom doit contenir au moins deux caractères.")
        chiffres = re.sub(r"\D", "", telephone)
        if len(chiffres) < 8:
            raise ValueError("Saisissez un numéro de téléphone valide (au moins 8 chiffres).")
        with self.connexion() as db:
            membre = db.execute("SELECT * FROM membres WHERE telephone_normalise=?", (chiffres,)).fetchone()
            if membre:
                if membre["nom"].casefold() != nom.casefold():
                    raise ValueError("Ce numéro est déjà associé à un autre membre. Chaque membre doit avoir son propre numéro.")
                return membre, False
            prochain = db.execute("SELECT COUNT(*) + 1 FROM membres").fetchone()[0]
            matricule = f"BIB-{date.today():%Y}-{prochain:04d}"
            try:
                db.execute("INSERT INTO membres(matricule,nom,telephone,telephone_normalise,cree_le) VALUES(?,?,?,?,?)",
                           (matricule, nom, telephone, chiffres, date.today().isoformat()))
            except sqlite3.IntegrityError as erreur:
                if "telephone_normalise" in str(erreur):
                    raise ValueError("Ce numéro est déjà attribué à un membre.") from erreur
                raise
            return db.execute("SELECT * FROM membres WHERE matricule=?", (matricule,)).fetchone(), True

    def rechercher_livres(self, terme: str = "") -> list[sqlite3.Row]:
        like = f"%{terme.strip()}%"
        with self.connexion() as db:
            return db.execute(
                "SELECT * FROM livres WHERE titre LIKE ? OR auteur LIKE ? OR categorie LIKE ? ORDER BY titre",
                (like, like, like),
            ).fetchall()

    def livre(self, livre_id: int):
        with self.connexion() as db:
            return db.execute("SELECT * FROM livres WHERE id=?", (livre_id,)).fetchone()

    def emprunts_actifs(self, matricule: str) -> list[sqlite3.Row]:
        with self.connexion() as db:
            return db.execute("""
                SELECT e.*, l.titre, l.auteur, l.categorie, l.annee, m.nom, m.telephone
                FROM emprunts e JOIN livres l ON l.id=e.livre_id
                JOIN membres m ON m.matricule=e.matricule
                WHERE e.matricule=? AND e.rendu_le IS NULL ORDER BY e.a_rendre_le
            """, (matricule,)).fetchall()

    def emprunter(self, livre_id: int, matricule: str) -> sqlite3.Row:
        aujourd_hui = date.today()
        echeance = aujourd_hui + timedelta(days=DUREE_PRET_JOURS)
        with self.connexion() as db:
            livre = db.execute("SELECT * FROM livres WHERE id=?", (livre_id,)).fetchone()
            if not livre:
                raise ValueError("Ce livre n'existe pas dans le catalogue.")
            membre = db.execute("SELECT * FROM membres WHERE matricule=?", (matricule,)).fetchone()
            if not membre:
                raise ValueError("Membre introuvable. Recommencez avec votre nom et téléphone.")
            actifs = db.execute("SELECT COUNT(*) FROM emprunts WHERE matricule=? AND rendu_le IS NULL", (matricule,)).fetchone()[0]
            if actifs >= MAX_PRETS_ACTIFS:
                raise ValueError(f"La limite de {MAX_PRETS_ACTIFS} emprunts actifs est atteinte.")
            retard = db.execute("SELECT 1 FROM emprunts WHERE matricule=? AND rendu_le IS NULL AND a_rendre_le<? LIMIT 1",
                                (matricule, aujourd_hui.isoformat())).fetchone()
            if retard:
                raise ValueError("Un emprunt est en retard. Rendez-le avant d'en faire un autre.")
            modifie = db.execute("UPDATE livres SET disponibles=disponibles-1 WHERE id=? AND disponibles>0", (livre_id,)).rowcount
            if not modifie:
                raise ValueError("Aucun exemplaire de ce livre n'est disponible.")
            curseur = db.execute("INSERT INTO emprunts(livre_id,matricule,emprunte_le,a_rendre_le) VALUES(?,?,?,?)",
                                 (livre_id, matricule, aujourd_hui.isoformat(), echeance.isoformat()))
            return db.execute("""
                SELECT e.*, l.titre,l.auteur,l.categorie,l.annee,m.nom,m.telephone
                FROM emprunts e JOIN livres l ON l.id=e.livre_id JOIN membres m ON m.matricule=e.matricule
                WHERE e.id=?
            """, (curseur.lastrowid,)).fetchone()

    def retourner(self, emprunt_id: int, matricule: str) -> sqlite3.Row:
        with self.connexion() as db:
            emprunt = db.execute("""
                SELECT e.*,l.titre,l.auteur,l.categorie,l.annee,m.nom,m.telephone
                FROM emprunts e JOIN livres l ON l.id=e.livre_id JOIN membres m ON m.matricule=e.matricule
                WHERE e.id=? AND e.matricule=? AND e.rendu_le IS NULL
            """, (emprunt_id, matricule)).fetchone()
            if not emprunt:
                raise ValueError("Emprunt actif introuvable pour ce membre.")
            rendu = date.today().isoformat()
            db.execute("UPDATE emprunts SET rendu_le=?, statut='Rendu' WHERE id=?", (rendu, emprunt_id))
            db.execute("UPDATE livres SET disponibles=disponibles+1 WHERE id=?", (emprunt["livre_id"],))
            return dict(emprunt) | {"rendu_le": rendu, "statut": "Rendu"}

    def retards(self) -> list[sqlite3.Row]:
        with self.connexion() as db:
            return db.execute("""
                SELECT e.*,l.titre,l.auteur,m.nom,m.telephone
                FROM emprunts e JOIN livres l ON l.id=e.livre_id JOIN membres m ON m.matricule=e.matricule
                WHERE e.rendu_le IS NULL AND e.a_rendre_le<? ORDER BY e.a_rendre_le
            """, (date.today().isoformat(),)).fetchall()


class HistoriqueModel:
    """Base dédiée, append-only, pour la trace des mouvements de l'application."""

    def __init__(self, chemin: Path = BASE_HISTORIQUE) -> None:
        self.chemin = chemin
        self.chemin.parent.mkdir(parents=True, exist_ok=True)

    def initialiser(self) -> None:
        with sqlite3.connect(self.chemin) as db:
            db.execute("""CREATE TABLE IF NOT EXISTS mouvements (
                id INTEGER PRIMARY KEY AUTOINCREMENT, date_heure TEXT NOT NULL,
                type_mouvement TEXT NOT NULL, matricule TEXT, nom_membre TEXT,
                telephone TEXT, livre_id INTEGER, titre_livre TEXT,
                emprunt_id INTEGER, details TEXT NOT NULL
            )""")

    def enregistrer(self, type_mouvement: str, details: str, membre=None, livre=None, emprunt_id=None) -> None:
        from datetime import datetime
        with sqlite3.connect(self.chemin) as db:
            db.execute("""INSERT INTO mouvements(date_heure,type_mouvement,matricule,nom_membre,telephone,
                livre_id,titre_livre,emprunt_id,details) VALUES(?,?,?,?,?,?,?,?,?)""",
                (datetime.now().astimezone().isoformat(timespec="seconds"), type_mouvement,
                 membre["matricule"] if membre else None, membre["nom"] if membre else None,
                 membre["telephone"] if membre else None, livre["id"] if livre else None,
                 livre["titre"] if livre else None, emprunt_id, details))

    def lister(self, limite: int = 100) -> list[sqlite3.Row]:
        with sqlite3.connect(self.chemin) as db:
            db.row_factory = sqlite3.Row
            return db.execute("SELECT * FROM mouvements ORDER BY id DESC LIMIT ?", (limite,)).fetchall()
