# Dossier de candidature — Label « Projet innovant »
 
**Projet :** Medad — Commerce Partnership OS  
**Version du dossier :** 0.1 — 2 novembre 2026  
**Statut :** DOCUMENT DE TRAVAIL — NON SOUMIS  
**Référentiel technique examiné :** `Loofy147/Medad`, branche `feat/medad-commerce-os-foundation`  
**Statut de cette branche :** 190 commits en avance sur `main`, 0 en retard au moment de la comparaison. Elle n'est pas la branche par défaut.

> Ce dossier décrit l'état réel du prototype et une proposition de validation. Il ne prétend pas démontrer une demande commerciale, des revenus, des clients, des contrats, des partenariats signés, une rentabilité ou une nouveauté mondiale. Les points non prouvés sont identifiés comme hypothèses ou inconnues.

---

## 1. Proposition du projet

### Description courte pour le champ Startup.dz (moins de 400 caractères)

> Medad est un outil B2B de décision pour les partenariats e-commerce en Algérie. Il relie des preuves datées sur les produits, fournisseurs et livraisons à une simulation du coût réel par commande — livrée, refusée, retournée et conservée — puis bloque les décisions risquées tant que les preuves et seuils requis ne sont pas réunis.

**Longueur :** 343 caractères (espaces compris), à recontrôler dans le formulaire avant dépôt.

### Résumé exécutif

Medad vise à aider les opérateurs de commerce électronique et leurs partenaires financiers ou opérationnels à décider si une opportunité de vente mérite un test limité, doit être corrigée ou doit être abandonnée avant d'engager du stock et des dépenses publicitaires.

Le produit réunit dans un flux cohérent :
1. un registre d'affirmations et de preuves datées sur un produit, un fournisseur, un transporteur, les coûts et les résultats ;
2. un moteur déterministe d'économie unitaire tenant compte des commandes non livrées, retours, récupération de stock, coûts logistiques et acquisition ;
3. des portes de décision qui empêchent le passage à une étape supérieure lorsque les éléments requis sont absents, périmés ou contradictoires ;
4. un paquet de décision traçable et un flux d'événements Instant ;
5. une préparation d'offres de partenariat transparentes, dont les responsabilités, coûts, risques et règles de partage restent à convenir par les parties.

**Périmètre initial :** logiciel B2B d'aide à la décision et de coordination. Le produit ne vend pas lui-même les marchandises et n'exécute pas les transactions, campagnes ou paiements dans son état actuel.

---

## 2. Problème ciblé et utilisateurs

### Problème à vérifier auprès du marché

Dans un modèle de vente avec paiement à la livraison (COD), une commande enregistrée n'est pas nécessairement une vente conservée. Les décisions d'achat de stock et de publicité peuvent être prises à partir de prix affichés, de coûts incomplets ou de taux supposés. Les frais d'expédition échouée, de retour, de traitement et la valeur récupérable du stock peuvent changer le résultat économique.

Les discussions de partenariat peuvent également laisser des zones grises : qui finance le stock, qui le possède, qui assume un retour, qui approuve la publicité, comment le bénéfice net est calculé et quand les comptes sont rapprochés.

**Important :** la fréquence et l'intensité de ces difficultés pour les segments visés n'ont pas encore été établies par des entretiens ou des données d'utilisateurs Medad. Le problème est une hypothèse commerciale à valider, même si le contexte COD est documenté à l'échelle nationale.

### Segments prioritaires — hypothèses

- **Opérateurs e-commerce algériens :** vendeurs et petites équipes qui évaluent des produits, achètent du stock et gèrent des commandes COD.
- **Partenaires de financement ou d'exploitation :** personnes ou structures qui financent/acquièrent le stock, le conservent ou organisent l'expédition en partenariat avec un opérateur.
- **À ne pas présumer :** taille du segment adressable, disposition à payer, fréquence d'usage et canal d'acquisition.

### Tâche principale du client

Avant d'engager du stock ou une campagne, répondre à quatre questions :
- Quelles données soutiennent le prix, le coût d'achat, les frais de livraison et le taux de réussite ?
- Quel est le résultat par commande placée, livrée et conservée, après les coûts réellement supportés ?
- Quelles preuves manquent et quelle vérification réduit le plus le risque ?
- Quelles responsabilités chaque partenaire accepte-t-il avant le lancement ?

---

## 3. Contexte du marché — données de référence, pas TAM

Le rapport de la CNUCED *Algérie — Évaluation de l'état de préparation au commerce électronique* (publication 2025, données de périodes explicitement indiquées) rapporte notamment :
- 90 % des répondants à son enquête consommateurs (1 338 réponses) ont déclaré avoir utilisé le paiement à la livraison pour des achats en ligne en 2023.
- Le rapport estime les ventes B2C en ligne en Algérie à 262 milliards DZD en 2023, soit 0,8 % du PIB, sur la base d'une combinaison de sources et de méthodes décrites dans le rapport.
- 3 988 commerçants étaient enregistrés sous l'activité de commerce électronique à fin mars 2024 ; environ 254 e-fournisseurs étaient estimés conformes aux dispositions de la loi 18-05.
- Les paiements en ligne pour les biens ne représentaient que 0,8 % du total des paiements en ligne pour les biens et services marchands à fin 2024 ; les données disponibles ne mesurent pas fiablement le volume total COD.

**Interprétation limitée :** ces données montrent un contexte où le COD a une place importante et où la formalisation du commerce en ligne est un enjeu. Elles ne prouvent ni la demande pour Medad, ni le nombre de clients potentiels, ni la volonté de payer, ni la rentabilité du produit.

Source : [CNUCED, rapport Algérie eTrade Readiness Assessment (2025)](https://unctad.org/system/files/official-document/dtlecde2025d3_en.pdf), notamment pages 18–20 du rapport.

---

## 4. Produit et expérience opérationnelle

### Flux proposé

`Opportunité produit`
→ `SKU et spécification exacts`
→ `échantillon inspecté`
→ `deux devis fournisseurs comparables`
→ `coût rendu documenté`
→ `conditions transporteur / COD`
→ `économie unitaire et sensibilité`
→ `test limité`
→ `cohorte de commandes rapprochée`
→ `revue humaine de passage à l'échelle`

Chaque étape conserve les références, dates, périmètres et limites des preuves. Un champ inconnu n'est pas traité comme un coût nul ou un résultat favorable.

### Modules déjà présents dans la branche technique examinée

| Module | Rôle documenté | Limite actuelle |
|---|---|---|
| Registre des preuves et des affirmations | Source, date, portée, statut et contradiction | Une référence de preuve ne prouve pas à elle seule l'authenticité externe |
| Moteur d'économie unitaire | Commandes placées, livrées, échouées, retournées, conservées, coûts, contribution, profit modélisé, CAC et seuil de rentabilité | Les résultats dépendent des données saisies et des hypothèses du modèle |
| Sensibilité | Scénarios de stress déterministes et seuils | Ce ne sont ni des probabilités ni des prévisions calibrées |
| Portes d'opportunité | SKU, échantillon, devis, coût rendu, transporteur, campagne et cohortes | Les contrôles exigent des preuves structurées ; les artefacts externes restent à joindre et à vérifier |
| Workflow de décision | Paquet d'analyse haché reliant économie, preuves, portes, sensibilité et Instant | Analyse locale sans autorisation d'action externe |
| Store SQLite local | Transactions, révisions, contrôles de rôles de test et chaîne d'audit | Stockage sur hôte local ; identité d'acteur du CLI non authentifiée pour un service distant |
| Instant | Événements calculés à partir d'un instantané de calcul | Pas d'abonnement à des flux de marché, commandes, livraison ou publicité en direct |
| Interface | Prototype web en arabe RTL, navigation entre aperçu, Instant, produits, calcul, propositions | Le store local n'est pas encore connecté automatiquement à l'interface par une API serveur de production |

### Exemple de logique économique

Le moteur distingue :
- commandes placées ;
- commandes livrées et commandes échouées ;
- commandes retournées après livraison ;
- commandes conservées ;
- chiffre d'affaires sur les commandes conservées ;
- coût produit retenu et perte de stock non récupérable ;
- emballage, transport aller, logistique d'échec, transport retour, manutention, publicité et coûts fixes ;
- CAC par commande placée et par commande conservée ;
- seuil de dépense publicitaire nulle ou positif uniquement lorsque la contribution hors publicité couvre les coûts fixes.

Si la contribution avant publicité ne couvre pas les coûts fixes, le moteur renvoie un seuil non disponible au lieu d'inventer un budget de rentabilité nul. La note de qualité des données est un indicateur heuristique de couverture et de fraîcheur, pas une probabilité de vérité, de demande ou de profit.

---

## 5. Caractère innovant revendiqué

**Positionnement à défendre :** l'innovation réside dans l'assemblage opérationnel d'une chaîne de décision vérifiable adaptée aux partenariats e-commerce COD, et non dans une affirmation de nouveauté mondiale ou dans la simple présence d'une IA.

### Différenciation fonctionnelle

1. **Preuve avant score :** les entrées sont reliées à une source, une date, une portée et une classe de preuve ; les contradictions ne sont pas moyennées.
2. **Économie basée sur le résultat conservé :** les coûts des commandes échouées, refusées et retournées influencent le calcul, plutôt que de traiter une commande enregistrée comme une vente finale.
3. **Portes explicites :** le système exige des éléments traçables avant le test ou l'examen d'une montée en échelle — notamment SKU exact, échantillon, devis distincts, frais du transporteur et cohortes rapprochées.
4. **Décision reproductible :** un paquet d'exécution conserve l'identité des entrées et du rapport ; le rejeu idempotent et les contrôles d'intégrité réduisent les divergences entre analyses.
5. **Séparation analyse/autorisation :** un résultat positif ne donne pas au logiciel le droit d'acheter, de commander du stock, de dépenser en publicité ou de signer un partenariat.

### Limite de la revendication

Aucune recherche structurée de brevets, de liberté d'exploitation ou de comparaison concurrentielle complète n'a été réalisée dans ce dossier. Aucun droit de propriété intellectuelle, brevet, marque enregistrée ou récompense n'est actuellement documenté ici. Il faudra démontrer l'originalité par l'analyse comparative et les preuves du fonctionnement, pas par une formule marketing.

---

## 6. Modèle économique

### Modèle envisagé — à valider

**B2B logiciel**, avec :
- abonnement par espace de travail ou équipe ;
- éventuellement une prestation initiale d'intégration / mise en place ;
- éventuellement des fonctions avancées de reporting ou de gouvernance selon le niveau d'usage.

Aucun prix, revenu, contrat, taux de conversion ou renouvellement n'est établi. Le pricing doit être validé par entretiens et propositions payantes réelles.

### Deux flux à ne pas confondre

- **Revenu de Medad :** rémunération de l'accès au logiciel et de services optionnels.
- **Résultat de l'activité commerciale d'un partenariat client :** recettes de vente moins coûts et pertes convenus entre les partenaires. Le moteur ne choisit ni la part de bénéfice ni les obligations contractuelles.

### Hypothèses de test

- Le client accepte de payer pour éviter une mauvaise décision de stock ou de publicité.
- Les données nécessaires peuvent être collectées sans charge excessive.
- Les équipes et partenaires préfèrent un registre partagé de preuves, coûts et décisions à des feuilles et messages dispersés.
- La valeur créée dépasse le coût de collecte, de vérification et de mise à jour des preuves.

Ces hypothèses restent **OPEN** jusqu'à validation.

---

## 7. État d'avancement et preuves techniques

### Identité de la source

- Dépôt : [Loofy147/Medad](https://github.com/Loofy147/Medad)
- Branche examinée : [feat/medad-commerce-os-foundation](https://github.com/Loofy147/Medad/tree/feat/medad-commerce-os-foundation)
- Comparaison observée : 190 commits en avance, 0 en retard par rapport à `main`.
- Cette branche n'est pas la branche par défaut ; les fonctions décrites ici ne doivent pas être présentées comme intégrées à `main`.

### Sources de code examinées

- [README de la branche](https://github.com/Loofy147/Medad/blob/feat/medad-commerce-os-foundation/README.md)
- [Modèle produit et contrat de preuves](https://github.com/Loofy147/Medad/blob/feat/medad-commerce-os-foundation/docs/PRODUCT_MODEL.md)
- [Méthode opérationnelle](https://github.com/Loofy147/Medad/blob/feat/medad-commerce-os-foundation/docs/OPERATING_METHOD.md)
- [Recherche marché du 29 octobre 2026](https://github.com/Loofy147/Medad/blob/feat/medad-commerce-os-foundation/docs/MARKET_RESEARCH.md)
- [Moteur d'économie unitaire](https://github.com/Loofy147/Medad/blob/feat/medad-commerce-os-foundation/engine/engine.py)
- [Portes de préparation des opportunités](https://github.com/Loofy147/Medad/blob/feat/medad-commerce-os-foundation/engine/opportunity.py)
- [Workflow de décision](https://github.com/Loofy147/Medad/blob/feat/medad-commerce-os-foundation/engine/workflow.py)
- [Moteur de sensibilité](https://github.com/Loofy147/Medad/blob/feat/medad-commerce-os-foundation/engine/sensitivity.py)
- [Interface prototype](https://github.com/Loofy147/Medad/blob/feat/medad-commerce-os-foundation/index.html)
- [Workflow CI des tests](https://github.com/Loofy147/Medad/blob/feat/medad-commerce-os-foundation/.github/workflows/tests.yml)

### Classification des preuves

| Affirmation | Statut | Base et limite |
|---|---|---|
| Un prototype web local existe | **OBSERVÉ** | `index.html` sur la branche mentionnée |
| Un moteur Python déterministe existe | **OBSERVÉ** | Sources de `engine/` examinées |
| Des fichiers de tests unitaires existent | **OBSERVÉ** | Plusieurs fichiers `engine/test_*.py` et workflow CI présents |
| Une pipeline CI est configurée pour exécuter les tests et vérifier l'interface | **OBSERVÉ** | `.github/workflows/tests.yml` |
| Les tests de cette révision ont tous réussi dans la présente revue | **UNKNOWN** | Aucun résultat de run CI courant n'a été obtenu dans cette revue ; ne pas annoncer PASS sans artefact |
| Le système est opérationnel en production avec comptes et équipes isolés | **CONTRADICTED** | Le README indique l'absence d'authentification de production, d'API serveur connectée et de multi-tenant |
| Les produits proposés ont une demande vérifiée ou une rentabilité démontrée | **CONTRADICTED** | Les quatre candidats du snapshot sont `RESEARCH_ONLY` |
| Il existe des fournisseurs, contrats transporteurs, campagnes ou cohortes réelles connectés | **UNKNOWN / NON ÉTABLI** | Pas d'intégration directe ni de documents de transactions clients établis |
| Des clients paient déjà Medad | **UNKNOWN / NON ÉTABLI** | Aucun revenu ou contrat client documenté |
| L'innovation est nouvelle au niveau mondial ou brevetable | **UNKNOWN** | Pas d'étude d'antériorité ni de recherche brevets réalisée |

### État du benchmark produit

La recherche datée du 29 octobre 2026 contient quatre candidats avec des annonces/prix publics, pas des ventes effectives :
- organiseur d'espace entre sièges de voiture ;
- support téléphone voiture ;
- panier de rangement à quatre compartiments ;
- kit spray/brosse de nettoyage d'écran.

Aucun n'est accepté comme gagnant. Il manque notamment des devis grossistes comparables, un échantillon inspecté, un coût rendu, des conditions transporteur liées au vendeur, des cohortes de commandes rapprochées et une campagne réconciliée. Ces exemples servent à illustrer le protocole, pas à démontrer une opportunité commerciale pour Medad.

---

## 8. Plan de validation — 90 jours proposés

Les cibles suivantes sont des objectifs de travail à approuver ; elles ne représentent pas des résultats déjà obtenus.

| Période proposée | Expérience | Preuve attendue | Porte de sortie |
|---|---|---|---|
| Jours 1–15 | 12 entretiens structurés : 8 opérateurs e-commerce et 4 partenaires potentiels | Comptes rendus anonymisés, problèmes récurrents, alternatives, coût de la mauvaise décision, disposition à payer | Arrêter ou reformuler si les problèmes ne sont pas récurrents ou si les solutions existantes suffisent |
| Jours 16–30 | 3 parcours « concierge » sur données historiques consenties et expurgées | Temps de préparation, champs indisponibles, corrections, décision avant/après, objections | Continuer si les utilisateurs peuvent fournir les données et jugent le rapport utile |
| Jours 31–60 | 2 équipes pilotes maximum, sans achat ou dépense effectués par Medad | SKU exact, échantillon inspecté, 2 devis indépendants, coût rendu, conditions COD, données réelles | Aucun stock ni budget publicitaire sans accord humain et conditions écrites |
| Jours 61–75 | Rapprocher au moins 2 cohortes temporelles distinctes par pilote si les opérations réelles le permettent | Commandes placées, livrées, échouées, retournées, conservées, dépenses publicitaires et pièces de preuve | Refaire les calculs ; ne pas mélanger des périodes qui se chevauchent ou des SKU différents |
| Jours 76–90 | Test de prix B2B et revue du modèle de revenus | Offre payante testée, refus documentés, prix accepté, coûts d'acquisition et de support estimés | Poursuivre uniquement si un client accepte une valeur et un prix mesurables |

### Mesures du pilote

- temps entre la collecte d'une opportunité et la décision vérifiée ;
- proportion des entrées critiques liées à une preuve valide et récente ;
- nombre de décisions bloquées par absence ou contradiction de preuve ;
- contribution avant publicité par commande conservée ;
- CAC par commande conservée, pas seulement par commande enregistrée ;
- écarts entre le résultat simulé et les résultats des cohortes réelles ;
- temps de rapprochement des comptes et désaccords entre partenaires ;
- volonté de payer et usage répété.

Aucun objectif de taux de conversion ou de rentabilité n'est annoncé avant le pilote et la disponibilité de dénominateurs réels.

---

## 9. Conformité, données et sécurité

Le produit est conçu au départ comme un outil B2B de décision. Les pilotes pourraient toutefois contenir des données de vendeurs, de partenaires, de contacts ou de commandes. Avant tout usage réel, il faut :
- définir les rôles de responsable du traitement et, le cas échéant, de sous-traitant ;
- minimiser les données personnelles et expurger les identifiants client qui ne sont pas nécessaires au calcul ;
- préciser finalités, base légale, information, droits, conservation, suppression et export ;
- définir le contrôle d'accès, la séparation des espaces, la sauvegarde, le chiffrement et la journalisation ;
- vérifier les obligations de la loi algérienne 18-07 telle que modifiée et complétée par la loi 25-11 du 24 juillet 2025 ;
- examiner l'applicabilité de la loi 18-05 sur le commerce électronique selon le rôle réellement exercé par chaque acteur du flux commercial.

**État actuel :** aucune conformité juridique complète n'est revendiquée. Le store du prototype est local et mono-hôte ; l'authentification et l'isolation de clients en production ne sont pas établies.

Sources officielles :
- [Portail du droit algérien — loi 18-07, modifiée par la loi 25-11 de 2025](https://droit.mjustice.gov.dz/fr/content/protection-des-personnes-physiques-dans-le-traitement-des-donn%C3%A9es-%C3%A0-caract%C3%A8re-personnel)
- [Ministère du Commerce — loi 18-05 relative au commerce électronique](https://commerce.gov.dz/reglementation/loi-n-deg-18-05)

---

## 10. Risques principaux et réponses

| Risque | Conséquence possible | Réponse prévue |
|---|---|---|
| Les opérateurs ne ressentent pas suffisamment le problème | Faible adoption et absence de revenus | Entretiens, parcours concierge, critères d'arrêt explicites |
| Données réelles insuffisantes ou de mauvaise qualité | Calculs précis en apparence mais faux | Provenance obligatoire, fraîcheur, contradiction, UNKNOWN par défaut |
| Conditions de transporteur mal modélisées | CAC et marge erronés | Devis vendeur/route précis, mise à jour et rapprochement réel |
| Utilisateurs confondent prévision et vérité | Décision de stock prématurée | Statuts de preuve visibles, gates, autorisation humaine séparée |
| Absence d'authentification et d'isolation multi-client | Exposition de données commerciales | Ne pas ouvrir un SaaS multi-client avant l'architecture de sécurité et les tests d'isolation |
| Règles et responsabilités de partenariat ambiguës | Conflits de stock, pertes ou profits | Modèle de contrat à faire examiner ; aucune part automatique dans le logiciel |
| Dépendance à un fournisseur de données | Prix périmés et coût récurrent | Interfaces substituables, export, cache daté, fournisseur alternatif |

---

## 11. Équipe, fondateurs et accompagnement

Les informations suivantes doivent être ajoutées par le porteur du projet dans le portail officiel et les pièces privées. Elles ne sont pas inventées dans ce dossier :
- identité légale, NIN, coordonnées et adresse ;
- CV, qualifications et expériences de chaque fondateur ;
- membres du projet, répartition des rôles et engagement ;
- statut d'incubation et attestation, si applicable ;
- inscription éventuelle dans le cadre de la décision ministérielle 1275 ;
- titres de propriété intellectuelle, récompenses ou attestations pertinentes, uniquement si disponibles.

**Ne pas placer de NIN, pièce d'identité, adresse privée, numéro personnel, certificat confidentiel ou donnée d'accès dans ce dépôt Git public.** Les joindre uniquement dans l'espace officiel sécurisé, après vérification de la destination.

---

## 12. Correspondance avec le formulaire Startup.dz

Le formulaire officiel actuel demande notamment :
- tous les champs remplis en caractères latins ;
- informations du demandeur, CV, wilaya et adresse ;
- nom du projet, secteur, description courte limitée à 400 caractères ;
- pitch deck préparé selon le modèle téléchargeable du portail ;
- présentation détaillée du projet et de l'innovation ;
- photo du prototype et stade d'avancement ;
- modèle économique B2B/B2C/B2G/autre ;
- site web, statut d'incubation, type d'incubateur, éventuelle inscription au titre de la décision 1275 ;
- titres de propriété intellectuelle et documents justificatifs, le cas échéant ; concours/récompenses.

**Règle de dépôt :** le portail demande le modèle de pitch deck qu'il héberge. Le PowerPoint préparé avec ce dossier est un brouillon de contenu structuré, pas une copie certifiée de ce canevas officiel. Il faut obtenir le modèle depuis le portail et y transférer le contenu avant le dépôt final.

### Éléments connus / à compléter

| Champ | Préparation actuelle |
|---|---|
| Nom du projet | Medad |
| Description courte | Texte proposé en section 1 ; vérifier la limite dans le formulaire |
| Secteur | À choisir dans les options proposées par le portail ; probablement service numérique/logiciel, valeur exacte non vérifiée |
| Modèle économique | B2B — hypothèse à confirmer |
| Stade d'avancement | Prototype / preuve de concept, selon l'option exacte disponible |
| Pitch deck | Brouillon distinct livré avec ce dossier ; à transposer dans le canevas officiel |
| Présentation détaillée | Sections 2 à 10 du présent document |
| Photo du prototype | Captures authentiques à prendre depuis l'interface locale ; ne pas remplacer par une maquette illustrative |
| Site web | Aucun site produit public vérifié dans cette revue ; ne pas inventer une URL |
| Incubateur / attestation | Inconnu, à vérifier |
| Décision ministérielle 1275 | Inconnu, à vérifier |
| Propriété intellectuelle | Aucun titre documenté dans cette revue |
| Prix / concours | Aucun prix documenté dans cette revue |
| Identité / CV / coordonnées | À compléter en privé sur le portail |

### Situation juridique du parcours

Le portail Startup.dz distingue explicitement le label « Projet innovant », destiné aux porteurs qui n'ont pas encore créé leur société, du label « Startup », destiné à une société déjà créée. L'article 17 du décret exécutif modifié en 2021 prévoit la candidature d'une personne physique ou d'un groupe de personnes physiques ; il mentionne, le cas échéant, les titres IP, récompenses, preuve d'un niveau doctoral pour au moins la moitié de l'équipe, attestation d'incubation et présentation d'un PoC ou prototype.

Il ne faut donc pas mélanger les pièces propres au label « Startup » (registre du commerce, NIF, statuts, comptes sociaux selon ancienneté) avec la voie initiale du « Projet innovant ».

Sources :
- [Startup.dz — formulaire Label projet innovant](https://startup.dz/label-projet/)
- [Startup.dz — distinction Projet innovant / Startup](https://startup.dz/pour-les-startups/)
- [Journal officiel n° 84 du 4 novembre 2021, décret exécutif n° 21-422, articles 8 et 17 modifiés](https://www.joradp.dz/FTP/jo-francais/2021/F2021084.pdf)

---

## 13. Décision proposée

**Décision recommandée :** poursuivre la préparation du dossier « Projet innovant » comme dossier de candidature en construction, et non comme candidature prête à déposer.

Les trois éléments qui amélioreraient le plus sa solidité sont :
1. une validation client documentée sur le problème et la volonté de payer ;
2. une démonstration authentique du prototype avec un cas réel expurgé et une comparaison entre une décision non structurée et le flux Medad ;
3. une revue technique exécutée sur la branche de référence, avec tests/CI actuels, limites de sécurité, et feuille de route production.

Le passage à une soumission officielle dépend aussi des informations personnelles et de l'équipe, du statut juridique réel, de l'accompagnement éventuel, et de la disponibilité du canevas officiel. Aucun formulaire n'a été soumis et aucune déclaration n'a été faite au nom du porteur.

---

## Sources officielles et pièces techniques

1. [Startup.dz — Label projet innovant](https://startup.dz/label-projet/)
2. [Startup.dz — Pour les startups](https://startup.dz/pour-les-startups/)
3. [Journal officiel n° 84 (2021), décret exécutif n° 21-422](https://www.joradp.dz/FTP/jo-francais/2021/F2021084.pdf)
4. [CNUCED — Évaluation de l'état de préparation au commerce électronique en Algérie (2025)](https://unctad.org/system/files/official-document/dtlecde2025d3_en.pdf)
5. [Loi 18-07 modifiée par la loi 25-11 (portail du droit algérien)](https://droit.mjustice.gov.dz/fr/content/protection-des-personnes-physiques-dans-le-traitement-des-donn%C3%A9es-%C3%A0-caract%C3%A8re-personnel)
6. [Loi 18-05 (Ministère du Commerce)](https://commerce.gov.dz/reglementation/loi-n-deg-18-05)
7. [Medad — branche technique examinée](https://github.com/Loofy147/Medad/tree/feat/medad-commerce-os-foundation)
