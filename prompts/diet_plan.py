DIET_PLAN_PROMPT = """
En tant que nutritionniste expert, génère un plan de régime basé sur :

Données utilisateur :
- Prénom: {user_data.get('first_name', 'Utilisateur')}
- Taille: {user_data.get('height', '?')} cm
- Poids actuel: {user_data.get('current_weight', '?')} kg
- Objectif: {user_data.get('target_weight', '?')} kg
- Date cible: {user_data.get('target_date', '?')}
- Âge: {user_data.get('age', '?')} ans

Historique des conversations :
{history[-3:] if history else 'Pas d\'historique disponible'}

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