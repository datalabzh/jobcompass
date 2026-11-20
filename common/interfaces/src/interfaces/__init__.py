"""
__init__.py

Description : interfaces partagées par plusieurs briques de JobCompass.
Règles      : volontairement vide : on importe chaque classe par son chemin
              (from interfaces.i_use_case import IUseCase).
              Seules les interfaces utilisées par plusieurs briques vivent ici ;
              une interface propre à une brique vit dans cette brique (ex.
              extraction.interfaces), celles du stockage dans storage.interfaces.
              Des interfaces seulement, un fichier par interface : aucun contrat de
              données (voir contracts) et aucune logique métier.
"""
