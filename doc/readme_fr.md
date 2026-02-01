# Composants personnalisés Neviweb pour Home Assistant

[🇫🇷 Version anglaise](../README.md)

> 💛 **Vous appréciez cette intégration ?**
> Si vous souhaitez soutenir son développement, vous pouvez contribuer ici :
> [![Soutien via PayPal](https://cdn.rawgit.com/twolfson/paypal-github-button/1.0.0/dist/button.svg)](https://www.paypal.me/phytoressources/)

Composants personnalisés pour la prise en charge des appareils Miwi [Neviweb](https://neviweb.com/) dans [Home Assistant](http://www.home-assistant.io).
Neviweb est une plateforme créée par Sinopé Technologies pour interagir avec ses appareils connectés tels que les thermostats, les interrupteurs/variateurs 
de lumière et les contrôleurs de charge. Il prend également en charge certains appareils fabriqués par
[Ouellet](http://www.ouellet.com/en-ca/products/thermostats-and-controls/neviweb%C2%AE-wireless-communication-controls.aspx).

Neviweb (Sinope Neviweb dans HACS) gère les appareils Miwi connectés au portail Neviweb via une passerelle GT125.

Ce composant_personnalisé a été mise à jour pour permettre la gestion des appareils provenant de deux réseaux GT125 connectés à Neviweb. Vous pouvez ainsi 
gérer simultanément les appareils de votre domicile et de votre bureau, ou de votre résidence secondaire. Les deux passerelles doivent être des GT125. 
Elles ne sont pas compatibles avec les GT130 ni les appareils Wi-Fi. Utilisez le composant personnalisé [Neviweb](https://github.com/claudegel/sinope-1) 
pour cette configuration.

Signaler un problème ou suggérer une amélioration : [Ouvrir un ticket](https://github.com/claudegel/sinope-1/issues/new/choose)

## Table des matières

- [Appareils supportées](#appareils-supportes)
- [Prérequis](#prerequis)
- [Installation](#installation)
- [Configuration](#configuration)
- [GT125](#passerelle-gt125)
- [Compteur de requêtes Neviweb](#compteur-de-requetes-quotidiennes)
- [Services / Actions](#services-personnalises)
- [Journalisation](#journalisation)
- [Éco-Sinopé](#recuperer-le-signal-eco-sinope-pour-la-période-de-pointe)
- [Statistiques d'énergie](#statistiques-energetiques)
- [Dépannage](#depannage)
- [Personnalisation](#customization)
- [Réinitialisation](#reinitialisation-materielle-de-lappareil)
- [Limitations](#limitations-actuelles)
- [TO DO](#a-faire)

## Appareils supportes
Liste des appareils actuellement pris en charge. En résumé, il s'agit de tous les appareils pouvant être ajoutés à Neviweb en tant 
qu'appareils Miwi.
- Thermostats
  - Sinopé TH1120RF-3000, thermostat de ligne
  - Sinopé TH1120RF-4000, thermostat de ligne
  - Sinopé TH1121RF-3000, thermostat de ligne, aires publiques
  - Sinopé TH1121RF-4000, thermostat de ligne, aires publiques
  - Sinopé TH1300RF, thermostat de sol
  - Sinopé TH1400RF, thermostat bas voltage
  - Sinopé TH1500RF, thermostat bipolaire
  - *Ouellet OTH2750-GT, thermostat de ligne
  - *Ouellet OTH3600-GA-GT, thermostat de sol
  - *Ouellet OTH4000-GT, thermostat de ligne
  - *Flextherm INSTINCT Connect thermostat
- Éclairage
  - Sinopé SW2500RF, Interrupteur
  - Sinopé DM2500RF, gradateur 
- Contrôleur de puissance
  - Sinopé RM3200RF, Contrôleur de charge 40A
  - Sinopé RM3250RF, Contrôleur de charge 50A
- Passerelle
  - GT125

*Non testé, mais devrait fonctionner correctement. Vos commentaires sont les bienvenus si un appareil ne fonctionne pas.

## Prerequis
Vous devez connecter vos appareils à une passerelle web GT125 et les ajouter à votre portail Neviweb avant de pouvoir 
interagir avec eux dans Home Assistant. Veuillez consulter le manuel d'utilisation de votre appareil ou visiter la page 
d'assistance Neviweb : [https://www.sinopetech.com/blog/support-cat/plateforme-nevi-web/].

Trois composants personnalisés vous permettent de gérer vos appareils via le portail Neviweb ou directement via votre passerelle GT125 :

- [Neviweb](https://github.com/claudegel/sinope-1) (HACS : Sinope Neviweb), ce composant personnalisé permet de gérer vos appareils via le portail Neviweb.
- [Sinope](https://github.com/claudegel/sinope-gt125) (HACS : Sinope GT125), composant personnalisé permettant de gérer vos appareils directement via votre passerelle web GT125.
- [Neviweb](https://github.com/claudegel/sinope-1) (HACS : Sinope Neviweb), composant personnalisé permettant de gérer vos appareils Zigbee connectés à votre passerelle GT130 et Wi-Fi via le portail Neviweb.

Il vous suffit d'en installer un seul, mais les trois peuvent être utilisés simultanément sur HA.

## Installation
### Composant personnalisé Neviweb pour gérer votre appareil via le portail Neviweb :

Il existe deux méthodes pour installer ce composant personnalisé :
- **Via le composant HACS** :
- Ce dépôt est compatible avec le Home Assistant Community Store
([HACS](https://community.home-assistant.io/t/custom-component-hacs/121727)).
- Après avoir installé HACS, installez « Sinope Neviweb » depuis le Store et utilisez l’exemple de fichier configuration.yaml ci-dessous.
- **Manuellement par téléchargement direct** :
- Téléchargez le fichier ZIP de ce dépôt à l’aide du bouton de téléchargement vert en haut à droite.
- Extrayez le fichier ZIP sur votre ordinateur, puis copiez l’intégralité du dossier `custom_components` dans votre répertoire `config` de Home Assistant
(où se trouve votre fichier `configuration.yaml`).
- Votre répertoire `config` devrait ressembler à ceci :
    ```
    config/
      configuration.yaml
      custom_components/
        neviweb/
          __init__.py
          light.py
          switch.py
          climate.py
          const.py
          helpers.py
          manifest.json
          services.yaml
          sensor.py
      ...
    ```

## Configuration

Pour activer la gestion Neviweb dans votre installation, ajoutez ce qui suit à votre fichier `configuration.yaml`,
puis redémarrez Home Assistant.
```yaml
# Example configuration.yaml entry
neviweb:
  username: '<Votre courriel Neviweb>'
  password: '<Votre mot de passe Neviweb>'
  network: '<Votre premier emplacement dans Neviweb>'
  network2: '<Votre second emplacement dans Neviweb>'
  scan_interval: 540
```

**Options de Configuration:**  

| key | required | default | description
| --- | --- | --- | ---
| **username** | Oui |  | Votre adresse e-mail utilisée pour vous connecter à Neviweb.|
| **password** | Oui |  | Votre mot de passe Neviweb.|
| **network** | Non | 1er emplacement trouvé | Le nom du premier GT125 que vous souhaitez contrôler.|
| **network2** | Non | 2e emplacement trouvé | Le nom du deuxième emplacement GT125 que vous souhaitez contrôler.|
| **scan_interval** | Non | 540 | Le nombre de secondes entre deux accès à Neviweb pour mettre à jour l'état de l'appareil.|

Sinopé a demandé un intervalle minimum de 5 minutes entre les interrogations. Vous pouvez donc réduire scan_interval à 300. 
Ne dépassez pas 600, sinon la session expirera.

Si vous possédez également un GT130 connecté à Neviweb, le paramètre réseau est obligatoire, sinon
il est possible que lors de la configuration, le réseau du GT130 soit détecté par erreur. Si vous ne possédez que deux réseaux GT125,
vous pouvez omettre leurs noms, car lors de la configuration, les deux premiers réseaux détectés seront automatiquement sélectionnés.
Si vous préférez ajouter des noms de réseau, assurez-vous qu'ils soient écrits « exactement » comme dans Neviweb.
(avec ou sans majuscule initiale).

## Passerelle GT125
Il est désormais possible de savoir si votre GT125 est toujours en ligne ou hors ligne avec Neviweb grâce à l'attribut gateway_status.
Le GT125 est détecté comme sensor.neviweb_sensor_gt125

## Compteur de requetes quotidiennes
Sinopé étant de plus en plus strict sur le nombre de requêtes quotidiennes, limité à 30 000, si vous atteignez cette limite, vous serez 
déconnecté jusqu'à minuit. Ceci est très problématique si vous utilisez plusieurs appareils ou si vous développez sur Neviweb. 
J'ai donc ajouté un compteur de requêtes Neviweb quotidiennes qui est remis à zéro à minuit et survit au redémarrage de Home Assistant. 
Ce compteur cré un capteur, `sensor.neviweb_daily_requests`, qui s'incrémente à chaque requête : mise à jour, interrogation des 
statistiques, statut d'erreur, etc.

Ainsi, vous pouvez augmenter l'intervalle de scan pour obtenir une fréquence plus rapide sans dépasser la limite.
Lorsque 25 000 requêtes seront atteintes, Neviweb enverra une notification. Ce seuil d'alerte sera configurable ultérieurement.

## Services personnalises
Les automatisations nécessitent des services pour pouvoir envoyer des commandes, par exemple : `light.turn_on`. Pour les appareils 
Neviweb connectés au GT125, il est possible d'utiliser des services personnalisés pour envoyer des informations spécifiques aux 
appareils ou modifier certains de leurs paramètres.

Ces services personnalisés sont accessibles via l'outil de développement (Actions) ou peuvent être utilisés dans l'automatisation.

- neviweb.set_second_display : permet de modifier l'affichage secondaire du thermostat, en passant de la température de consigne à la
  température extérieure. Cette commande ne doit être envoyée qu'une seule fois à chaque appareil.
- neviweb.set_climate_keypad_lock : permet de verrouiller le clavier de l'appareil de climatisation.
- neviweb.set_light_keypab_lock : permet de verrouiller le clavier de l'appareil d'éclairage.
- neviweb.set_switch_keypab_lock : permet de verrouiller le clavier de l'interrupteur.
- neviweb.set_light_timer : permet de définir un délai avant l'extinction automatique de la lumière.
- neviweb.set_switch_timer : permet de définir un délai avant la fermeture automatique de l'interrupteur.
- neviweb.set_led_indicator : permet de modifier la couleur et l'intensité du voyant LED des appareils d'éclairage pour indiquer leur état
  « allumé » et « éteint ». Vous pouvez envoyer n'importe quelle couleur de la liste RGB via les trois paramètres de couleur rouge, vert
  et bleu et vous pouvez régler l'intensité de l'indicateur LED.
- neviweb.set_time_format : pour afficher l'heure au format 12 h ou 24 h sur les thermostats.
- neviweb.set_temperature_format : pour afficher la température au format Celsius ou Fahrenheit sur les thermostats.
- neviweb.set_early_start : pour activer le démarrage anticipé du chauffage sur le thermostat.
- neviweb.set_backlight : pour activer ou désactiver le rétroéclairage des thermostats.
- neviweb.set_wattage : pour définir la limite de puissance (wattageOverload) des luminaires.
- neviweb.set_setpoint_min : pour définir la température de consigne minimale des thermostats.
- neviweb.set_setpoint_max : pour définir la température de consigne maximale des thermostats.
- neviweb.set_light_away_mode : pour définir le mode d'éclairage lorsque le thermostat est désactivé.
- neviweb.set_switch_away_mode : pour définir le mode d'interrupteur lorsque le thermostat est désactivé.
- neviweb.set_cycle_length : permet de régler la durée du cycle principal du thermostat basse tension. Valeurs possibles :
  « 15 s », « 5 min », « 10 min », « 15 min », « 20 min », « 25 min », « 30 min ».
- neviweb.set_aux_cycle_length : permet de régler la durée du cycle et la puissance du chauffage auxiliaire du thermostat basse tension.
  Valeurs possibles : « 15 s », « 5 min », « 10 min », « 15 min », « 20 min », « 25 min », « 30 min ». Pour activer/désactiver
  le chauffage d'appoint, utilisez le bouton situé en bas de la carte du thermostat.
- neviweb.set_eco_status : permet d'activer/désactiver le mode éco des thermostats.
- neviweb.set_switch_eco_status : permet d'activer/désactiver le mode éco de l'interrupteur.
- neviweb.set_em_heat : permet d'activer/désactiver le chauffage d'appoint/de secours.
- neviweb.set_neviweb_status, pour modifier le statut global domicile/absence de Neviweb.

## Journalisation
Le fichier home-assistant.log n'étant plus disponible, nous avons ajouté un nouveau système de journalisation qui enregistre toutes 
les données de journalisation de Neviweb dans un fichier `neviweb_log.txt` de votre fichier de configuration. Ce fichier est écrasé 
à chaque redémarrage de Home Assistant et est archivé lorsqu'il atteint 2 Mo. La rotation des journaux génère ainsi quatre fichiers au total.

## Recuperer le signal Eco Sinope pour la période de pointe

Si vous avez au moins un thermostat ou un régulateur de charge enregistré auprès du programme Éco Sinopé, il est désormais possible de détecter
le moment où Neviweb envoie le signal de préchauffage pour les thermostats ou le signal de démarrage pour le régulateur de charge.
Trois attributs ont été ajoutés pour anticiper les périodes de pointe :
- Pour les thermostats :
  - eco_status : réglé sur 0 en période normale, sur 1 pendant le préchauffage et les périodes de pointe.
  - eco_power : réglé sur 0 en fonctionnement normal, sur 1 si le thermostat chauffe pendant les périodes de pointe.
  - eco_optout : réglé sur 0 en fonctionnement normal pendant les périodes de pointe, sur 1 si la consigne du thermostat a été modifiée
    pendant les périodes de pointe.
- Pour le régulateur de charge :
  - eco_status : réglé sur « none » en fonctionnement normal, sur « active » 10 minutes avant les périodes de pointe et sur « planned »
    pendant les périodes de pointe.

Il est alors possible de mettre en place une automatisation pour préparer tous les appareils pour la période de pointe.

## Statistiques energetiques

Deux attributs ont été ajoutés pour suivre la consommation d'énergie des appareils :
- hourly_kwh : kWh consommés au cours de la dernière heure.
- daily_kwh : kWh consommés au cours de la dernière journée.

Ces données sont extraites de Neviweb toutes les 30 minutes, à partir de 5 minutes après le redémarrage de HA.

### Suivez votre consommation d'energie sur le tableau de bord HA Energy.

Lorsque les attributs énergétiques sont disponibles, il est possible de suivre la consommation d'énergie de chaque 
appareil dans le tableau de bord énergétique de Home Assistant en créant un [capteur modèle](https://www.home-assistant.io/integrations/template/) :
```yaml
template:
  - sensor:
      - name: "consommation d'énergie cuisine"
        unit_of_measurement: "kWh"
        device_class: energy
        state_class: total
        state: >-
          {{ state_attr("climate.neviweb_climate_kitchen","hourly_kwh") }}
      - name: "Kitchen energy daily"
        unit_of_measurement: "kWh"
        device_class: energy
        state_class: total
        state: >-
          {{ state_attr("climate.neviweb_climate_kitchen","daily_kwh") }}
```

## Depannage

Le fichier home-assistant.log n'est plus disponible et a été remplacé par un fichier nommé neviweb_log.txt dans votre répertoire 
de configuration. Ce fichier contient uniquement les journaux relatifs à ce composant personnalisé. Le nouveau système de 
journalisation crée un fichier vide au démarrage et effectue une rotation des journaux chaque fois que sa taille atteint 2 Mo.

Pour vous aider au mieux, veuillez fournir un extrait de votre fichier `neviweb_log.txt`. J'y ai ajouté quelques messages de 
journalisation de débogage qui pourraient faciliter le diagnostic du problème.

Vous pouvez également poster votre question dans l'une de ces discussions pour obtenir de l'aide :
- https://community.home-assistant.io/t/sinope-line-voltage-thermostats/17157
- https://community.home-assistant.io/t/adding-support-for-sinope-light-switch-and-dimmer/38835

### Activation des messages de débogage Neviweb dans le fichier `neviweb_log.txt`

Ajoutez ces lignes à votre fichier `configuration.yaml`
   ```yaml
   logger:
     default: warning
     logs:
       custom_components.neviweb: debug
       homeassistant.service: debug
       homeassistant.config_entries: debug
   ```
Cela définira le niveau de journalisation par défaut sur « avertissement » pour tous vos composants, à l'exception de Neviweb qui affichera 
des messages plus détaillés.

### Messages d'erreur reçus de Neviweb
Vous trouverez ces messages de Neviweb dans votre journal :

- VALINVLD : Valeur invalide envoyée à Neviweb.
- SVCINVREQ : Requête invalide envoyée à Neviweb : service inexistant ou requête malformée.
- DVCCOMMTO : Délai de communication avec l'appareil dépassé : l'appareil ne répond pas assez rapidement ou vous l'interrogez trop fréquemment.
- DVCACTNSPTD : Action de l'appareil non prise en charge. L'appel de service n'est pas pris en charge pour cet appareil.
- USRSESSEXP : Session utilisateur expirée. Réduisez votre intervalle de scan à moins de 6 minutes, sinon votre session sera interrompue.
- ACCSESSEXC : Trop de sessions ouvertes simultanément. Cela se produit généralement si vous redémarrez Home Assistant plusieurs fois et/ou
  si vous avez également une session ouverte sur Neviweb.
- DVCUNVLB : Appareil indisponible. Neviweb ne parvient pas à se connecter à l'appareil.
- SVCERR : Erreur de service. Service indisponible. Veuillez réessayer ultérieurement.

Si vous trouvez d'autres codes d'erreur, veuillez me les transmettre.

## Customization
Install  [Custom-Ui](https://github.com/Mariusthvdb/custom-ui) custom_component via HACS and add the following in your code:

Icons for heat level: create folder www in the root folder .homeassistant/www
copy the six icons there. You can find them under local/www
feel free to improve my icons and let me know. (See icon_view2.png)

For each thermostat add this code in `customize.yaml`
```yaml
climate.neviweb_climate_thermostat_name:
  templates:
    entity_picture: >
      if (attributes.heat_level < 1) return '/local/heat-0.png';
      if (attributes.heat_level < 21) return '/local/heat-1.png';
      if (attributes.heat_level < 41) return '/local/heat-2.png';
      if (attributes.heat_level < 61) return '/local/heat-3.png';
      if (attributes.heat_level < 81) return '/local/heat-4.png';
      return '/local/heat-5.png';
 ```  
 Dans `configuration.yaml`, ajoutez ceci
```yaml
customize: !include customize.yaml
```

## Reinitialisation materielle de l'appareil

Pour réinitialiser vos appareils :
- Lampe et variateur : Appuyez sur le bouton inférieur et maintenez-le enfoncé pendant au moins 20 secondes. La LED
  clignotera en jaune. Appuyez ensuite rapidement deux fois sur le bouton supérieur. La LED clignotera trois fois en rouge.
  
## Limitations actuelles
- Home Assistant ne prend pas en charge la sélection du mode de fonctionnement pour les éléments « gradateur » et « interrupteur ».
  Vous ne verrez donc aucune liste déroulante dans l'interface utilisateur vous permettant de basculer entre les modes Automatique
  et Manuel. Le mode actuel est uniquement visible dans les attributs.

- Si vous recherchez le mode Absence dans la fiche « Thermostat » Lovelace, vous devez cliquer sur le bouton à trois points situé
  en haut à droite de la fiche. Une fenêtre s'ouvrira alors, affichant le commutateur du mode Absence en bas.

## A FAIRE

- Explorer comment configurer automatiquement des capteurs dans Home Assistant qui signaleront l'état d'un attribut
- spécifique d'un appareil.
  (i.e. the wattage of a switch device)
- register a new service to change operation_mode and another one to set away mode.
