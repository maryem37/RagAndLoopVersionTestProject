Feature: Gestion des Demandes de Congé

Scenario: Valide une demande de congé avec dates valides
  Given un utilisateur connecté
  When il soumet une demande de congé avec des dates valides
  Then la demande doit être en attente d'approbation

Scenario: Valide une demande de congé avec des dates non valides
  Given un utilisateur connecté
  When il soumet une demande de congé avec des dates non valides
  Then la demande doit être rejetée et l'utilisateur informé de l'erreur

Scenario: Annule une demande de congé en attente d'approbation
  Given un utilisateur connecté ayant une demande de congé en attente d'approbation
  When il annule sa demande
  Then la demande doit être annulée et l'utilisateur informé que sa demande a été annulée

Scenario: Valide plusieurs demandes de congés simultanément
  Given un utilisateur connecté ayant plusieurs demandes de congés en attente d'approbation
  When il valide toutes les demandes
  Then toutes les demandes doivent être approuvées et l'utilisateur informé que toutes ses demandes ont été approuvées

Scenario: Valide une demande de congé avec des jours fériés
  Given un utilisateur connecté ayant une demande de congé avec des jours fériés
  When il valide la demande
  Then la demande doit être approuvée et l'utilisateur informé que sa demande a été approuvée

Scenario: Valide une demande de congé supérieure à son quota
  Given un utilisateur connecté ayant atteint son quota de congés
  When il soumet une demande de congé supérieure à son quota
  Then la demande doit être rejetée et l'utilisateur informé que sa demande a été rejetée en raison de son quota de congés atteint

Scenario: Valide une demande de congé inférieure à son quota
  Given un utilisateur connecté ayant une demande de congé inférieure à son quota
  When il valide la demande
  Then la demande doit être approuvée et l'utilisateur informé que sa demande a été approuvée

Scenario: Valide une demande de congé pour un employé non disponible
  Given un utilisateur connecté ayant une demande de congé pour un employé non disponible
  When il valide la demande
  Then la demande doit être rejetée et l'utilisateur informé que l'employé est indisponible pendant cette période

Scenario: Valide une demande de congé avec des heures supérieures à celles autorisées
  Given un utilisateur connecté ayant une demande de congé avec des heures supérieures à celles autorisées
  When il valide la demande
  Then la demande doit être rejetée et l'utilisateur informé que sa demande a été rejetée en raison d'heures supérieures à celles autorisées