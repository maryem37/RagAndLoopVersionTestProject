Feature: Gestion des Demandes de Congé

Scenario: Validez une demande de congé avec dates valides et durée valide
  Given un utilisateur connecté
  When il soumet une demande de congé avec des dates valides et une durée valide
  Then la demande doit être enregistrée avec succès

Scenario: Validez une demande de congé avec des dates non valides
  Given un utilisateur connecté
  When il soumet une demande de congé avec des dates non valides
  Then l'erreur doit être affichée et la demande ne doit pas être enregistrée

Scenario: Validez une demande de congé avec une durée inférieure à la limite minimale
  Given un utilisateur connecté
  When il soumet une demande de congé avec une durée inférieure à la limite minimale
  Then l'erreur doit être affichée et la demande ne doit pas être enregistrée

Scenario: Validez une demande de congé avec une durée supérieure à la limite maximale
  Given un utilisateur connecté
  When il soumet une demande de congé avec une durée supérieure à la limite maximale
  Then l'erreur doit être affichée et la demande ne doit pas être enregistrée

Scenario: Validez une demande de congé pour un utilisateur ayant déjà utilisé sa quota annuel
  Given un utilisateur connecté qui a atteint son quota annuel
  When il soumet une demande de congé
  Then l'erreur doit être affichée et la demande ne doit pas être enregistrée

Scenario: Validez une demande de congé pour un utilisateur ayant déjà utilisé sa quota mensuel
  Given un utilisateur connecté qui a atteint son quota mensuel
  When il soumet une demande de congé
  Then l'erreur doit être affichée et la demande ne doit pas être enregistrée

Scenario: Validez une demande de congé pour un utilisateur ayant déjà utilisé sa quota hebdomadaire
  Given un utilisateur connecté qui a atteint son quota hebdomadaire
  When il soumet une demande de congé
  Then l'erreur doit être affichée et la demande ne doit pas être enregistrée

Scenario: Validez une demande de congé pour un utilisateur ayant déjà utilisé sa quota jour
  Given un utilisateur connecté qui a atteint son quota jour
  When il soumet une demande de congé
  Then l'erreur doit être affichée et la demande ne doit pas être enregistrée

Scenario: Validez une demande de congé avec un type de congé invalide
  Given un utilisateur connecté
  When il soumet une demande de congé avec un type de congé invalide
  Then l'erreur doit être affichée et la demande ne doit pas être enregistrée

Scenario: Validez une demande de congé avec un statut de congé invalide
  Given un utilisateur connecté
  When il soumet une demande de congé avec un statut de congé invalide
  Then l'erreur doit être affichée et la demande ne doit pas être enregistrée