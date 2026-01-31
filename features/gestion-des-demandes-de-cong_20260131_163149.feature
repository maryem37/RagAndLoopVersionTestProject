Feature: Gestion des Demandes de Congé

Scenario: Valide une demande de congé avec dates valides
  Given un utilisateur connecté
  When il soumet une demande de congé avec des dates valides
  Then la demande doit être en attente d'approbation

Scenario: Valide une demande de congé avec des dates non valides
  Given un utilisateur connecté
  When il soumet une demande de congé avec des dates non valides
  Then la demande doit être rejetée et l'utilisateur doit recevoir un message d'erreur

Scenario: Annule une demande de congé en attente d'approbation
  Given un utilisateur connecté ayant une demande de congé en attente d'approbation
  When il annule sa demande
  Then la demande doit être annulée et l'utilisateur doit recevoir un message de confirmation

Scenario: Annule une demande de congé déjà approuvée
  Given un utilisateur connecté ayant une demande de congé déjà approuvée
  When il annule sa demande
  Then la demande doit être rejetée et l'utilisateur doit recevoir un message d'erreur

Scenario: Valide plusieurs demandes de congés en même temps
  Given un utilisateur connecté ayant plusieurs demandes de congés à valider
  When il valide toutes les demandes
  Then toutes les demandes doivent être approuvées et l'utilisateur doit recevoir un message de confirmation

Scenario: Valide une demande de congé avec des jours fériés compris
  Given un utilisateur connecté ayant une demande de congé avec des jours fériés compris
  When il valide la demande
  Then la demande doit être approuvée et l'utilisateur doit recevoir un message de confirmation

Scenario: Valide une demande de congé avec des jours supérieurs à la limite autorisée
  Given un utilisateur connecté ayant une demande de congé avec des jours supérieurs à la limite autorisée
  When il valide la demande
  Then la demande doit être rejetée et l'utilisateur doit recevoir un message d'erreur

Scenario: Valide une demande de congé pour un employé en congé maladie
  Given un utilisateur connecté ayant une demande de congé pour un employé en congé maladie
  When il valide la demande
  Then la demande doit être rejetée et l'utilisateur doit recevoir un message d'erreur

Scenario: Valide une demande de congé pour un employé en congé parental
  Given un utilisateur connecté ayant une demande de congé pour un employé en congé parental
  When il valide la demande
  Then la demande doit être approuvée et l'utilisateur doit recevoir un message de confirmation