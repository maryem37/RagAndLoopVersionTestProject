Feature: Gestion des Demandes de Congé

Scenario: Validez une demande de congé valide
  Given un utilisateur connecté avec des droits d'administration
  When il soumet une demande de congé valide (jours supérieurs à la durée minimale et inférieurs à la durée maximale)
  Then la demande est enregistrée avec succès

Scenario: Validez une demande de congé invalide
  Given un utilisateur connecté avec des droits d'administration
  When il soumet une demande de congé invalide (jours inférieurs à la durée minimale ou supérieurs à la durée maximale)
  Then l'erreur est affichée et la demande n'est pas enregistrée

Scenario: Validez une demande de congé pour un utilisateur inactif
  Given un utilisateur inactif
  When il soumet une demande de congé valide
  Then l'erreur est affichée et la demande n'est pas enregistrée

Scenario: Validez une demande de congé pour un utilisateur avec des demandes en cours
  Given un utilisateur ayant des demandes en cours
  When il soumet une nouvelle demande de congé valide
  Then l'erreur est affichée et la demande n'est pas enregistrée

Scenario: Validez une demande de congé pour un utilisateur avec des demandes refusées
  Given un utilisateur ayant des demandes refusées
  When il soumet une nouvelle demande de congé valide
  Then l'erreur est affichée et la demande n'est pas enregistrée

Scenario: Annulez une demande de congé en cours
  Given un utilisateur connecté avec des droits d'administration ayant une demande de congé en cours
  When il annule la demande de congé
  Then la demande est annulée avec succès

Scenario: Annulez une demande de congé non en cours
  Given un utilisateur connecté avec des droits d'administration ayant une demande de congé déjà traitée ou annulée
  When il essaie d'annuler la demande de congé
  Then l'erreur est affichée et la demande n'est pas annulée

Scenario: Validez une demande de congé pour un utilisateur avec des demandes en attente
  Given un utilisateur ayant des demandes en attente
  When il soumet une nouvelle demande de congé valide
  Then la demande est ajoutée à la liste des demandes en attente

Scenario: Validez une demande de congé pour un utilisateur avec des demandes refusées et en attente
  Given un utilisateur ayant des demandes refusées et en attente
  When il soumet une nouvelle demande de congé valide
  Then la demande est ajoutée à la liste des demandes en attente