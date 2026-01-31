Feature: Demande de congé

  Scenario: Un employé peut demander un congé
    Given l'employé est connecté au système
    When il soumet une nouvelle demande de congé avec des dates valides
    Then la demande de congé doit être enregistrée et affichée dans sa liste de demandes

  Scenario: Un employé peut modifier une demande de congé existante
    Given l'employé est connecté au système et qu'il a une demande de congé en cours
    When il modifie les dates ou le motif de la demande de congé
    Then la demande de congé doit être mise à jour avec les nouvelles informations

  Scenario: Un employé peut annuler sa demande de congé
    Given l'employé est connecté au système et qu'il a une demande de congé en cours
    When il annule la demande de congé
    Then la demande de congé doit être supprimée de sa liste de demandes

  Scenario: Un employé ne peut pas demander un congé si les dates sont invalides
    Given l'employé est connecté au système et qu'il soumet une nouvelle demande de congé avec des dates invalides
    When il soumet la demande de congé
    Then le système doit afficher un message d'erreur et ne doit pas enregistrer la demande

  Scenario: Un employé ne peut pas annuler une demande de congé si elle est déjà approuvée
    Given l'employé est connecté au système et qu'il a une demande de congé approuvée
    When il tente d'annuler la demande de congé
    Then le système doit afficher un message d'erreur et ne doit pas annuler la demande

  Scenario: Un employé peut voir les détails de ses demandes de congé
    Given l'employé est connecté au système
    When il affiche sa liste de demandes de congé
    Then il doit pouvoir voir les détails de chaque demande, y compris les dates, le motif et l'état de la demande

  Scenario: Un employé ne peut pas voir les détails des demandes de congé d'autres employés
    Given un employé est connecté au système
    When il affiche la liste de demandes de congé d'un autre employé
    Then le système doit afficher un message d'erreur et ne doit pas révéler les informations des demandes de congé d'autres employés

  Scenario: Un employé peut voir la liste des demandes de congé approuvées par son gestionnaire
    Given l'employé est connecté au système et que son gestionnaire a approuvé une demande de congé
    When il affiche la liste des demandes de congé approuvées
    Then il doit pouvoir voir les détails de chaque demande, y compris les dates, le motif et l'état de la demande

  Scenario: Un employé ne peut pas voir la liste des demandes de congé approuvées par un autre gestionnaire
    Given un employé est connecté au système
    When il affiche la liste des demandes de congé approuvées par un autre gestionnaire
    Then le système doit afficher un message d'erreur et ne doit pas révéler les informations des demandes de congé approuvées par un autre gestionnaire