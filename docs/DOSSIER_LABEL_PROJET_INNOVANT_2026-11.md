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

> Medad est un outil de décision pour les partenariats e-commerce en Algérie. Il documente les preuves sur les produits, fournisseurs et coûts logistiques, calcule l’économie des commandes conservées et signale les données manquantes avant l’engagement du stock ou du budget publicitaire.

**Longueur :** 286 caractères (espaces compris), à recontrôler dans le formulaire avant dépôt.

### Résumé exécutif

Medad vise à aider les opérateurs de commerce électronique et leurs partenaires financiers ou opérationnels à décider si une opportunité de vente mérite un test limité, doit être corrigée ou doit être abandonnée avant d'engager du stock et des dépenses publicitaires.

Le produit réunit dans un flux cohérent :
1. un registre d'affirmations et de preuves datées sur un produit, un fournisseur, un transporteur, les coûts et les résultats ;
2. un moteur déterministe d'économie unitaire tenant compte des commandes non livrées, retours, récupération de stock, coûts logistiques et acquisition ;
3. des portes de décision qui empêchent le passage à une étape supérieure lorsque les éléments requis sont absents, périmés ou contradictoires ;
4. un paquet de décision traçable et un flux d'événements Instant ;
5. une préparation d'offres de partenariat transparentes, dont les responsabilités, coûts, risques et règles de partage restent à convenir par les parties.

**Périmètre actuel :** prototype local d'aide à la décision, pas une plateforme SaaS prête à commercialiser. **Modèle initial à tester :** un flux de partenariat réel entre un opérateur qui recherche et commercialise une opportunité et un partenaire qui finance/détient le stock et coordonne la préparation/livraison. Le logiciel ne vend pas lui-même les marchandises et n'exécute pas les transactions, campagnes ou paiements. Un abonnement SaaS ou des frais de service restent des hypothèses de monétisation, non des décisions validées.

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

### Concurrence et solutions de substitution — premier scan public

Le segment n'est pas vierge. KIO/KIOSTORE décrit une plateforme avec boutique, paiements CIB/Edahabia/COD, COD Shield, pixels publicitaires, analytics, Google Sheets, API de transporteurs et ERP. KIO affiche un plan gratuit et des tarifs annuels ramenés à environ 2 030 et 4 130 DZD/mois ; ses chiffres de marchands et ses performances sont des déclarations du fournisseur, pas des mesures indépendantes. [KIOSTORE](https://kio.dz/en/kiostore) · [KIO About](https://kio.dz/en/about)

Storix DZ décrit les commandes, le stock, les retours COD, les coûts de retour, les marges et des analyses ; sa page affiche 1 500 DZD/mois pour Pro et un essai de 30 jours ou 30 commandes. Storix indique ne pas être connecté directement aux transporteurs. Ses chiffres d'exemple sont signalés comme données de démonstration. [Storix DZ](https://storix-dz.com/)

goStore DZ décrit boutique, commandes, stock, intégration Ecotrack, statistiques, calcul de bénéfice net, gestion d'équipe et API selon l'offre. [goStore DZ](https://gostoredz.com/fr)

**Conséquence :** Medad ne peut pas revendiquer une innovation simplement fondée sur le calcul de marge, le suivi des retours, la gestion des commandes ou l'analytics COD. Le territoire à tester est plus étroit : décision pré-stock, comparaison de devis comparables, mesure du capital exposé et gouvernance d'un partenariat entre opérateur et financeur. Il faut confirmer par des essais produits que les plateformes existantes ne couvrent pas déjà cette tâche, seules ou avec un tableur.

Ce scan est un desk review de pages publiques daté du 2 novembre 2026. Les fonctionnalités/prix cités sont des affirmations des éditeurs ; aucun essai comparatif, référence client ou audit indépendant n'a été réalisé.

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

Si la contribution avant publicité ne couvre pas les coûts fixes, le moteur renvoie un seuil non disponible au lieu d'inventer un budget de rentabilité nul. La note de qualité des données est un indicateur heuristique de couverture et de fraîcheur, pas une probabilité de vérité, de demande ou de profit. Un grade HIGH n'est pas un intervalle de confiance statistique ; le seuil par défaut de 30 observations ne suffit pas à garantir une estimation précise des taux de livraison ou de retour.

---

## 5. Caractère innovant revendiqué

**Positionnement à tester, pas encore à revendiquer comme exclusif :** Medad pourrait différencier sa chaîne de décision pré-stock et de contrôle du risque de partenariat. Le calcul des marges COD, la gestion des retours et l'analytics existent déjà chez des concurrents. La valeur distinctive devra être prouvée sur un deal réel face à ces outils et à un tableur.

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

### Modèle initial à tester : partenariat opérationnel

Le premier scénario à valider n'est pas un abonnement SaaS présumé. Il s'agit d'un deal où :
- l'opérateur identifie une opportunité, documente les preuves, prépare l'offre et prend en charge l'acquisition commerciale ;
- le partenaire finance ou acquiert le stock, le détient/stocke et coordonne la préparation et la livraison ;
- les parties conviennent avant toute action de la propriété du stock, du plafond publicitaire, de la définition du bénéfice net, de la prise en charge des refus/retours/pertes et du calendrier de règlement.

Ce flux correspond au problème opérationnel que Medad doit d'abord résoudre pour son client-zéro. Il n'est pas encore démontré par un partenariat réel signé ou une cohorte observée.

### Monétisation — décision ouverte

Évaluer séparément :
- service d'évaluation/gestion de deal ou frais opérationnels ;
- frais par deal/pilote ;
- abonnement SaaS multi-équipe si l'usage répété et la collaboration entre plusieurs clients sont confirmés.

Aucun prix, revenu, contrat, taux de conversion, coût d'acquisition ou renouvellement n'est établi. Le payeur exact est inconnu : l'opérateur, le partenaire de capital, une agence ou une équipe commerciale peuvent avoir des budgets et des incitations différents.

### Hypothèses à tester

- le problème de décision pré-stock est assez coûteux et fréquent pour justifier un outil distinct ;
- les deux parties acceptent de fournir les documents et données nécessaires ;
- Medad améliore une décision réelle face à leur processus actuel et aux outils concurrents ;
- le bénéfice créé dépasse le coût humain de collecte, vérification, support et rapprochement.

Ces hypothèses restent **OPEN** jusqu'à validation. Le bénéfice du deal client et le revenu propre de Medad sont deux modèles économiques distincts.

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
| 118 méthodes de test sont présentes dans huit fichiers de test | **OBSERVÉ** | Inspection des fichiers `engine/test_*.py` sur la branche examinée |
| Les tests et la vérification frontend ont réussi pour la révision du dossier | **EXPERIMENTALLY_SUPPORTED** | [GitHub Actions run #359](https://github.com/Loofy147/Medad/actions/runs/41528768381), job `python-unit-economics` : les deux étapes ont réussi |
| Le run CI démontre une sécurité multi-tenant ou un parcours navigateur réel | **CONTRADICTED / NON COUVERT** | Le workflow exécute les tests Python et un script de vérification frontend ; il ne démontre pas l'authentification production, l'isolation réelle ni les intégrations live |
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

Les cibles suivantes sont des objectifs de travail à approuver ; elles ne représentent pas des résultats déjà obtenus. Ce programme est une découverte qualitative et un pilote contrôlé, pas une étude statistiquement représentative.

| Période proposée | Expérience | Preuve attendue | Porte de sortie |
|---|---|---|---|
| Jours 1–15 | 12 entretiens structurés : 8 opérateurs e-commerce et 4 partenaires potentiels, plus essais guidés de KIO, Storix et goStore | Comptes rendus anonymisés, processus actuel, alternatives, coût de la mauvaise décision, lacunes non couvertes, disposition à payer | Arrêter ou reformuler si les solutions existantes couvrent déjà le job ou si le problème n'est pas récurrent |
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
| Modèle économique | À déclarer après arbitrage : service B2B / autre selon l'offre réellement proposée ; l'abonnement SaaS n'est pas validé |
| Stade d'avancement | Prototype / preuve de concept, selon l'option exacte disponible |
| Pitch deck | Brouillon distinct livré avec ce dossier ; à transposer dans le canevas officiel |
| Présentation détaillée | Sections 2 à 10 du présent document |
| Photo du prototype | Capture authentique de l'interface réelle à produire ; aucun visuel de présentation ne remplace cette pièce |
| Site web | Aucun site produit public vérifié dans cette revue ; ne pas inventer une URL |
| Incubateur / attestation | Inconnu, à vérifier |
| Décision ministérielle 1275 | Inconnu, à vérifier |
| Propriété intellectuelle | Aucun titre documenté dans cette revue |
| Prix / concours | Aucun prix documenté dans cette revue |
| Identité / CV / coordonnées | À compléter en privé sur le portail |

### Situation juridique du parcours et éléments probatoires

Le portail Startup.dz distingue le label « Projet innovant », destiné aux porteurs qui n'ont pas encore créé leur société, du label « Startup », destiné à une société déjà créée.

L'article 17 du décret exécutif 20-254 de 2020 demande trois éléments de fond : (1) présentation du projet et de ses aspects innovants, (2) éléments établissant un **potentiel important de croissance économique**, et (3) qualifications scientifiques et/ou techniques et expérience de l'équipe. Les titres IP et récompenses sont à fournir le cas échéant. Le décret 21-422 de 2021 modifie l'article 17 et maintient ces trois premières lignes comme « sans changement » ; il ajoute des pièces conditionnelles telles que preuve qu'au moins la moitié des membres possèdent un doctorat, attestation d'incubation d'un incubateur labellisé, et présentation d'une preuve de concept ou d'un prototype.

Le décret 25-311, publié en décembre 2025, modifie d'autres dispositions du décret 20-254, notamment la composition/compétence du comité, des règles de renouvellement et la création du label « Entreprise accélérée ». Son texte ne réécrit pas l'article 17 relatif au label « Projet innovant ». Le cadre doit néanmoins être cité comme modification ultérieure du texte de base.

Le dossier actuel n'apporte pas encore la preuve du potentiel de croissance économique ni les éléments de CV/qualifications de l'équipe. Les chiffres macro de la CNUCED ne remplacent pas ces preuves propres à Medad. Pour construire ce dossier, il faut documenter un segment atteignable, un acheteur précis, un problème fréquent, des alternatives, un pilote et un chemin économique vérifiable.

Il ne faut pas mélanger les pièces propres au label « Startup » (registre du commerce, NIF, statuts, comptes sociaux selon ancienneté) avec la voie initiale du « Projet innovant ». Le formulaire en ligne demande toutefois séparément les coordonnées et justificatifs du demandeur et exige une photo du prototype ainsi que le canevas de présentation officiel.

Sources :
- [Startup.dz — formulaire Label projet innovant](https://startup.dz/label-projet/)
- [Startup.dz — distinction Projet innovant / Startup](https://startup.dz/pour-les-startups/)
- [Journal officiel 2020 — décret 20-254, article 17](https://www.joradp.dz/FTP/jo-arabe/2020/A2020055.pdf)
- [Journal officiel 2021 — décret 21-422, article 8 / article 17](https://www.joradp.dz/FTP/jo-francais/2021/F2021084.pdf)
- [Journal officiel 2025 — décret 25-311](https://www.joradp.dz/FTP/jo-arabe/2025/A2025081.pdf)

---

## 13. Décision proposée

**Décision recommandée : NE PAS SOUMETTRE À CE STADE.** Le dossier reste un brouillon de candidature.

Priorités avant toute soumission :
1. prouver le potentiel de croissance économique propre à Medad, et pas seulement le contexte macro du COD ;
2. compléter les CV, qualifications, rôles et engagement de l'équipe dans le dossier privé ;
3. exécuter un cas pilote face à KIO/Storix/goStore et au processus tableur, avec un résultat mesurable et un utilisateur qui accepte une offre payante ;
4. fournir une capture authentique du prototype et transférer le contenu dans le modèle exact de PitchDeck téléchargé depuis Startup.dz ;
5. documenter le modèle de partenariat réel, le payeur et l'exposition financière ;
6. établir les conditions minimales de sécurité et de conformité avant toute donnée personnelle réelle.

Le CI #359 est désormais PASS sur le code examiné ; cela ne lève aucun des blocages de demande, de croissance, d'authentification production ou de conformité. Aucune soumission ni déclaration n'a été faite au nom du porteur.

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
