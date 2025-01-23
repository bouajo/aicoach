DIET_PLAN_PROMPT = """
En tant que nutritionniste expert, génère un plan de régime basé sur :

Données utilisateur :
- Prénom: {first_name}
- IMC initial: {imc}
- Objectif: {weight_diff} kg en {weeks} semaines
- Historique: {diet_history}

Règles du régime :
1. Jeûne intermittent 16/8
2. Répartition nutritionnelle :
   - Protéines: 30%
   - Légumes: 50%
   - Glucides complexes: 20%
3. Hydratation :
   - 500ml au réveil
   - 1L entre 10h-12h
   - 1L entre 14h-18h
4. Suppléments recommandés :
   - Multivitamines le matin
   - Magnésium le soir

Étapes de génération :
1. Calculer le déficit calorique journalier
2. Décomposer en phases hebdomadaires
3. Prévoir des check-ins hebdomadaires
4. Adapter aux contraintes utilisateur
"""