Feature: Gestion des Demandes de Congé

Scenario: Validation d'une demande de congé pour un employé existant
  Given un employé existant avec un compte valide
  When je soumet une demande de congé pour cet employé
  Then la demande de congé doit être enregistrée et l'état de la demande doit être "En attente"

Scenario: Validation d'une demande de congé pour un employé inexistant
  Given un employé inexistant avec un compte valide
  When je soumet une demande de congé pour cet employé
  Then la demande doit être rejetée et l'erreur "Employé introuvable" doit être affichée

Scenario: Validation d'une demande de congé avec des dates invalides
  Given un employé existant avec un compte valide
  When je soumet une demande de congé avec des dates invalides (date de début supérieure à la date de fin)
  Then la demande doit être rejetée et l'erreur "Dates invalides" doit être affichée

Scenario: Validation d'une demande de congé avec une durée inférieure à la limite minimale
  Given un employé existant avec un compte valide
  When je soumet une demande de congé avec une durée inférieure à la limite minimale (par exemple, moins de 2 jours)
  Then la demande doit être rejetée et l'erreur "Durée insuffisante" doit être affichée

Scenario: Validation d'une demande de congé avec une durée supérieure à la limite maximale
  Given un employé existant avec un compte valide
  When je soumet une demande de congé avec une durée supérieure à la limite maximale (par exemple, plus de 30 jours)
  Then la demande doit être rejetée et l'erreur "Durée excessive" doit être affichée

Scenario: Validation d'une demande de congé avec une durée inférieure à la disponibilité du demandeur
  Given un employé existant avec un compte valide
  When je soumet une demande de congé avec une durée inférieure à la disponibilité du demandeur (par exemple, le demandeur a déjà pris des congés pendant cette période)
  Then la demande doit être rejetée et l'erreur "Durée incompatible avec la disponibilité du demandeur" doit être affichée

Scenario: Validation d'une demande de congé avec une durée inférieure à la disponibilité du service
  Given un employé existant avec un compte valide
  When je soumet une demande de congé avec une durée inférieure à la disponibilité du service (par exemple, le service n'est pas disponible pendant cette période)
  Then la demande doit être rejetée et l'erreur "Durée incompatible avec la disponibilité du service" doit être affichée

Scenario: Validation d'une demande de congé avec une justification insuffisante
  Given un employé existant avec un compte valide
  When je soumet une demande de congé sans justification ou avec une justification insuffisante
  Then la demande doit être rejetée et l'erreur "Justification insuffisante" doit être affichée

Scenario: Validation d'une demande de congé avec une justification valide
  Given un employé existant avec un compte valide
  When je soumet une demande de congé avec une justification valide
  Then la demande doit être enregistrée et l'état de la demande doit être "En attente"