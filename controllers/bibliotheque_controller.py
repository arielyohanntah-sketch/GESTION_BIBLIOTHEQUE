"""Contrôleur : orchestre les actions entre la vue et les modèles."""

from models.bibliotheque_model import BibliothequeModel, HistoriqueModel


class BibliothequeController:
    def __init__(self, bibliotheque: BibliothequeModel, historique: HistoriqueModel) -> None:
        self.bibliotheque = bibliotheque
        self.historique = historique
        self.membre = None

    def ouvrir_session(self, nom: str, telephone: str):
        self.membre, cree = self.bibliotheque.identifier_ou_creer_membre(nom, telephone)
        if cree:
            self.historique.enregistrer("INSCRIPTION", "Création d'une fiche membre", membre=self.membre)
        else:
            self.historique.enregistrer("CONNEXION", "Identification du membre", membre=self.membre)
        return self.membre, cree

    def rechercher_livres(self, terme: str = ""):
        return self.bibliotheque.rechercher_livres(terme)

    def emprunter(self, livre_id: int):
        emprunt = self.bibliotheque.emprunter(livre_id, self.membre["matricule"])
        membre = {"matricule": emprunt["matricule"], "nom": emprunt["nom"], "telephone": emprunt["telephone"]}
        livre = {"id": emprunt["livre_id"], "titre": emprunt["titre"]}
        self.historique.enregistrer(
            "EMPRUNT", f"Échéance : {emprunt['a_rendre_le']}; statut : En cours",
            membre=membre, livre=livre, emprunt_id=emprunt["id"],
        )
        return emprunt

    def mes_emprunts(self):
        return self.bibliotheque.emprunts_actifs(self.membre["matricule"])

    def retourner(self, emprunt_id: int):
        emprunt = self.bibliotheque.retourner(emprunt_id, self.membre["matricule"])
        membre = {"matricule": emprunt["matricule"], "nom": emprunt["nom"], "telephone": emprunt["telephone"]}
        livre = {"id": emprunt["livre_id"], "titre": emprunt["titre"]}
        self.historique.enregistrer(
            "RETOUR", f"Date de retour : {emprunt['rendu_le']}; statut : Rendu",
            membre=membre, livre=livre, emprunt_id=emprunt["id"],
        )
        return emprunt

    def retards(self):
        return self.bibliotheque.retards()

    def historique_recent(self):
        return self.historique.lister(30)
