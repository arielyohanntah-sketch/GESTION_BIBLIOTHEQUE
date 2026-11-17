"""Point d'entrée : construit les modèles, le contrôleur puis la vue MVC."""

from controllers.bibliotheque_controller import BibliothequeController
from models.bibliotheque_model import BibliothequeModel, HistoriqueModel
from views.console_view import ConsoleView


def main() -> None:
    bibliotheque = BibliothequeModel()
    historique = HistoriqueModel()
    bibliotheque.initialiser()
    historique.initialiser()
    ConsoleView(BibliothequeController(bibliotheque, historique)).demarrer()


if __name__ == "__main__":
    main()
