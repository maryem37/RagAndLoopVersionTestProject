Feature: Gestion des Demandes de Congé

Scenario: Validation d'une demande de congé pour un employé existant
  Given un employé existe déjà dans la base de données
  When une nouvelle demande de congé est soumise pour cet employé
  Then la demande de congé doit être enregistrée et l'état de la demande doit être "En attente"

Scenario: Validation d'une demande de congé pour un employé inexistant
  Given un employé n'existe pas dans la base de données
  When une nouvelle demande de congé est soumise pour cet employé
  Then l'erreur "Employé introuvable" doit être affichée

Scenario: Validation d'une demande de congé avec des dates invalides
  Given un employé existe dans la base de données
  When une nouvelle demande de congé est soumise avec des dates invalides (par exemple, date de début supérieure à la date de fin)
  Then l'erreur "Dates invalides" doit être affichée

Scenario: Validation d'une demande de congé avec une durée inférieure à la limite minimale
  Given un employé existe dans la base de données
  When une nouvelle demande de congé est soumise avec une durée inférieure à la limite minimale (par exemple, 1 jour)
  Then l'erreur "Durée de congé insuffisante" doit être affichée

Scenario: Validation d'une demande de congé avec une durée supérieure à la limite maximale
  Given un employé existe dans la base de données
  When une nouvelle demande de congé est soumise avec une durée supérieure à la limite maximale (par exemple, plus de 30 jours)
  Then l'erreur "Durée de congé excessive" doit être affichée

Scenario: Validation d'une demande de congé avec un type invalide
  Given un employé existe dans la base de données
  When une nouvelle demande de congé est soumise avec un type invalide (par exemple, "Vacances" au lieu de "Conge sans solde")
  Then l'erreur "Type de congé invalide" doit être affichée

Scenario: Validation d'une demande de congé avec une durée valide mais en dépassant la disponibilité du personnel
  Given un employé existe dans la base de données et que le personnel est occupé pendant les dates demandées
  When une nouvelle demande de congé est soumise pour ces dates
  Then l'erreur "Personnel indisponible" doit être affichée

Scenario: Validation d'une demande de congé avec une durée valide et en respectant la disponibilité du personnel
  Given un employé existe dans la base de données et que le personnel est disponible pendant les dates demandées
  When une nouvelle demande de congé est soumise pour ces dates
  Then la demande de congé doit être enregistrée et l'état de la demande doit être "En attente"

Scenario: Validation d'une demande de congé avec une durée valide, en respectant la disponibilité du personnel et avec un type valide
  Given un employé existe dans la base de données et que le personnel est disponible pendant les dates demandées
  When une nouvelle demande de congé est soumise avec un type valide pour ces dates
  Then la demande de congé doit être enregistrée et l'état de la demande doit être "En attente"

Scenario: Validation d'une demande de congé avec une durée valide, en respectant la disponibilité du personnel, avec un type valide et avec des justificatifs
  Given un employé existe dans la base de données et que le personnel est disponible pendant les dates demandées
  When une nouvelle demande de congé est soumise avec un type valide pour ces dates et avec des justificatifs
  Then la demande de congé doit être enregistrée et l'état de la demande doit être "En attente"