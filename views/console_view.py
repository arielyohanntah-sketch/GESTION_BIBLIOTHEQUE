"""Interface console : affiche les écrans et lit les saisies utilisateur."""

from datetime import date

from controllers.bibliotheque_controller import BibliothequeController


class ConsoleView:
    def __init__(self, controller: BibliothequeController) -> None:
        self.controller = controller

    def demarrer(self) -> None:
        print("=" * 64, "\n BIBLIOTHÈQUE MUNICIPALE — ACCUEIL", "\n", "=" * 64, sep="")
        while True:
            try:
                nom = input("Votre nom complet : ").strip()
                telephone = input("Votre numéro de téléphone : ").strip()
                membre, cree = self.controller.ouvrir_session(nom, telephone)
                print(("Fiche membre créée." if cree else "Bonjour, heureux de vous revoir."),
                      f"Votre matricule : {membre['matricule']}")
                break
            except ValueError as erreur:
                print(f"Saisie incorrecte : {erreur}\nRéessayez.\n")
        self._menu()

    def _menu(self) -> None:
        while True:
            print(f"\n--- {self.controller.membre['nom']} | {self.controller.membre['matricule']} ---")
            print("1. Rechercher dans le catalogue\n2. Emprunter un livre\n3. Mes emprunts et retourner un livre")
            print("4. Consulter les retards de la bibliothèque\n5. Consulter l'historique récent\n0. Quitter")
            choix = input("Votre choix : ").strip()
            try:
                if choix == "1":
                    self._rechercher()
                elif choix == "2":
                    self._emprunter()
                elif choix == "3":
                    self._mes_emprunts()
                elif choix == "4":
                    self._retards()
                elif choix == "5":
                    self._historique()
                elif choix == "0":
                    print("Session terminée. Conservez votre matricule pour votre prochaine visite.")
                    return
                else:
                    print("Choisissez une option du menu.")
            except (ValueError, TypeError) as erreur:
                print(f"Opération impossible : {erreur}")

    def _rechercher(self) -> None:
        terme = input("Titre, auteur ou catégorie (Entrée pour tout afficher) : ")
        livres = self.controller.rechercher_livres(terme)
        if not livres:
            print("Aucun livre ne correspond à la recherche.")
            return
        print(f"\n{len(livres)} livre(s) trouvé(s)")
        for livre in livres:
            print(f"[{livre['id']:03}] {livre['titre']} | {livre['auteur']} | {livre['categorie']} | "
                  f"{livre['annee']} | disponibles : {livre['disponibles']}/{livre['exemplaires']}")

    def _emprunter(self) -> None:
        self._rechercher()
        emprunt = self.controller.emprunter(int(input("Code du livre à emprunter : ")))
        print("\n" + "=" * 58 + "\n REÇU D'EMPRUNT — À CONSERVER\n" + "=" * 58)
        print(f"N° d'emprunt : {emprunt['id']}\nMembre : {emprunt['nom']}\nMatricule : {emprunt['matricule']}")
        print(f"Téléphone : {emprunt['telephone']}\nLivre : {emprunt['titre']}\nAuteur : {emprunt['auteur']}")
        print(f"Catégorie : {emprunt['categorie']}\nAnnée : {emprunt['annee']}")
        print(f"Date d'emprunt : {self._date_fr(emprunt['emprunte_le'])}")
        print(f"Date limite de retour : {self._date_fr(emprunt['a_rendre_le'])}\nStatut : {emprunt['statut']}")
        print(f"NB: Assurer vous de ramener le livre intacte tel que vous l'avez pris.")
        print("=" * 58)

    def _mes_emprunts(self) -> None:
        emprunts = self.controller.mes_emprunts()
        if not emprunts:
            print("Vous n'avez aucun emprunt actif.")
            return
        for emprunt in emprunts:
            retard = date.fromisoformat(emprunt["a_rendre_le"]) < date.today()
            print(f"N° {emprunt['id']} | {emprunt['titre']} — {emprunt['auteur']} | emprunté le "
                  f"{self._date_fr(emprunt['emprunte_le'])} | à rendre le {self._date_fr(emprunt['a_rendre_le'])}"
                  f" | {'EN RETARD' if retard else 'En cours'}")
        choix = input("Numéro d'emprunt à retourner (Entrée pour annuler) : ").strip()
        if choix:
            retour = self.controller.retourner(int(choix))
            print(f"Retour enregistré le {self._date_fr(retour['rendu_le'])}. Livre : {retour['titre']}.")

    def _retards(self) -> None:
        retards = self.controller.retards()
        if not retards:
            print("Aucun retard enregistré.")
            return
        print(f"{len(retards)} emprunt(s) en retard dans la bibliothèque :")
        for item in retards:
            print(f"N° {item['id']} | {item['titre']} — {item['auteur']} | {item['nom']} "
                  f"({item['telephone']}) | échéance {self._date_fr(item['a_rendre_le'])}")

    def _historique(self) -> None:
        mouvements = self.controller.historique_recent()
        if not mouvements:
            print("Aucun mouvement enregistré.")
            return
        print("\n30 derniers mouvements (base historique) :")
        for m in mouvements:
            membre = f"{m['nom_membre']} / {m['matricule']} / {m['telephone']}" if m['matricule'] else ""
            livre = f" | {m['titre_livre']} | emprunt n° {m['emprunt_id']}" if m['titre_livre'] else ""
            print(f"{m['date_heure']} | {m['type_mouvement']} | {membre}{livre} | {m['details']}")

    @staticmethod
    def _date_fr(iso: str) -> str:
        return date.fromisoformat(iso).strftime("%d/%m/%Y")
