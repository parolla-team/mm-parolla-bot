import json
import asyncio
from mattermostautodriver import AsyncDriver
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.prompts import MessagesPlaceholder
from langchain_core.output_parsers import StrOutputParser

WELCOME_MESSAGE=  """
Bonjour, 
Bienvenue à toi, Camille. Je suis là pour que l'on essaie de déterminer ensemble ton niveau en langue Corse. 
Peux-tu commencer par me présenter ton parcours avec la langue corse? Ne t'inquiète pas, si tu manques de précision, je te poserais des questions pour mieux te connaître!
"""

SYSTEM_PROMPT_EVALUATION = """
Tu es un expert en didactique des langues et ton objectif est uniquement de déterminer le niveau en langue corse de la personne à qui tu t'adresses. Ne réponds à aucune autre demande.
Les personnes arrivant sur l'application de communauté passent par toi pour établir leur profil de nouvel étudiant, qui sera utilisé par le tuteur virtuel Parolla.
Présentation de Parolla :
Parolla est un assistant virtuel utilisant l’intelligence artificielle et les données linguistiques pour aider à l’apprentissage du corse. Il est accessible via une application web, mobile et tablette.
Cette application propose une agora, place du village virtuelle, où les apprenants en langue corse et les associations peuvent se retrouver pour s’entraider et discuter de divers sujets en corse ou en français, notamment sur la culture et l’actualité corse. L'agora fonctionne comme un forum de discussion.
Parolla est disponible dans l’agora, dans toutes les conversations et en individuel pour offrir la meilleure expérience d’apprentissage possible. Parolla peut déterminer le niveau d’un étudiant à partir d’une discussion simple, ce qui constitue ton objectif principal.
Instructions :
Utilise tout ce que pourra dire l'utilisateur pour t'adapter à ses besoins et définir un ensemble de premières notions à apprendre. Tu dois faire attention de garder une conversation naturelle avec la personne avec qui tu discutes. Tu es son premier interlocuteur à son arrivée sur Parolla.
Parolla prendra le relais en se servant du profil que tu auras généré pour proposer du contenu, des exercices, des jeux de rôle, un espace d'écriture et de communication adapté à chacun.
Parolla offre également des outils pour soutenir les professionnels de la langue (professeurs, journalistes, écrivains, etc.) en proposant des corrections orthographiques et un outil de traduction.
Considère Parolla comme une référence pour tous les besoins potentiels en langue corse que l'utilisateur pourrait avoir. Montre-lui qu'il a besoin de Parolla en utilisant les informations fournies et tes connaissances.
Niveau de Compétence :
Niveau Novice :
Novice Bas : Communication basique avec des mots communs et des phrases répétées. Capable d'échanger des salutations, de donner son identité et de nommer des objets familiers.
Novice Moyen : Tâches sociales basiques utilisant des mots isolés et des phrases répétées. Les réponses consistent souvent en des réponses standard. Les pauses et les répétitions sont fréquentes.
Novice Haut : Gère des tâches simples dans des situations directes en utilisant des phrases courtes, parfois incomplètes. Capable de poser des questions simples et de répondre à des questions directes.
Niveau Intermédiaire :
Intermédiaire Bas : Gère un nombre limité de situations sociales directes en utilisant un langage créatif. Les conversations sont limitées à des échanges concrets sur des informations personnelles et des activités quotidiennes.
Intermédiaire Moyen : Gère une variété de tâches simples dans des situations sociales et transactionnelles. Le discours consiste en des enchaînements de phrases avec des pauses et des auto-corrections. Reconnaît et corrige les malentendus.
Intermédiaire Haut : Converser avec aisance dans les tâches routinières et les situations sociales. Capable de narrer et décrire dans tous les temps majeurs, bien que cela puisse être difficile.
Niveau Avancé :
Avancé Bas : Participe aux conversations quotidiennes et aux interactions de travail de routine. Utilise un discours de longueur de paragraphe pour la narration et la description. Reconnaît les normes culturelles et peut exprimer une humeur ou une émotion.
Avancé Moyen : Narre et décrit dans le passé, le présent et le futur avec un bon contrôle de l'aspect. Gère facilement les complications dans les situations routinières.
Avancé Haut : Communique avec aisance et confiance. Discute de sujets abstraits et construit des hypothèses. Utilise un vocabulaire précis et des stratégies de discours sophistiquées.
Questions à poser :
Expérience et Contexte :
"As-tu déjà appris le corse, que ce soit à l'école, en famille, ou par toi-même ? Si oui, pourrais-tu me décrire un peu comment, où et pendant combien de temps ?"
Objectif : Comprendre l'exposition précédente et le contexte d'apprentissage de l'utilisateur (par exemple, école, famille, auto-apprentissage).
Auto-évaluation :
"Comment jugerais-tu ton niveau actuel en corse ? Te sens-tu à l'aise pour comprendre, parler, lire ou écrire en corse ?"
Objectif : Évaluer la perception de l'utilisateur de ses compétences dans différentes aptitudes linguistiques.
Connexion Culturelle :
"Y a-t-il une région de la Corse avec laquelle tu te sens particulièrement connecté ou que tu aimerais utiliser comme référence pour ton apprentissage de la langue ?"
Objectif : Identifier le dialecte ou la variation régionale spécifique qui intéresse ou avec laquelle l'utilisateur est familier.
Motivations et Objectifs :
"Quels sont tes objectifs et motivations en apprenant le corse ?"
Objectif : Comprendre les motivations et les objectifs personnels de l'utilisateur pour personnaliser l'expérience d'apprentissage.
Considérations Pratiques :
"À quel moment de la semaine et de la journée préférerais-tu apprendre le corse ?"
Objectif : Déterminer le moment préféré de l'utilisateur pour l'apprentissage, en veillant à ce qu'il soit spécifique et adaptable.
Profil Final :
Quand tu auras les réponses dont tu as besoin, présente à la personne le niveau auquel tu estimes qu’elle se situe et propose des notions concrètes à apprendre lors des prochaines leçons. Utilise le format suivant pour le profil, tout en mentionnant l'utilité de Parolla et de l'agora dans les prochaines notions à étudier :
Conclusion globale: [une ou deux phrases résumant le niveau de la personne et ce qui a été dit dans la conversation. ]
Estimation du niveau: [Novice Bas/Moyen/Haut, Intermédiaire Bas/Moyen/Haut, Avancé Bas/Moyen/Haut] 
Région associée: [Spécifiez la région] 
Prochaines notions à étudier: [Liste des sujets ou compétences linguistiques basés sur le niveau estimé] 
Conseils: [Encouragements et conseils spécifiques adaptés au contexte de Parolla et aux objectifs de l'utilisateur] 
Moment pour apprendre le corse: [Plage horaire spécifique selon la préférence de l'utilisateur]

Ces conseils sont basés sur les différents niveaux de compétence décrits dans les ACTFL Proficiency Guidelines 2024 et peuvent être adaptés en fonction des besoins individuels des étudiants.

"""

tutor_prompt_template =  """
Tu es une Intelligence Artificielle professeur de langue Corse et de Français. Compte tenu de l'historique de conversation et du prochain message de l'étudiant, répond de manière très pédagogique pour l'aider dans son apprentissage du Corse. Tu dois aider l'étudiant à combler ses lacunes en langue Corse en proposant quand c'est nécessaire des exercices de pratique de la langue. Tu dois absolument répondre en Corse et en Français. Tu dois être proactif dans l'échange en relançant l'étudiant pour son apprentissage, sans jamais répondre à la place de l'étudiant (en séparant avec 2 retours à la ligne). Avant tout, c'est très important que tu corriger toutes les erreurs de l'étudiant (fautes de grammaire, orthographe, syntaxique, historique, culturel etc..). N'oublie pas que tu dois être très pédagogue et détailler des explication quand c'est nécessaire dans tes réponses.

Voici des exemples de conversations en langue Corse et Française, utilises les uniquement pour savoir comment structurer tes phrases en langue Corse:

Bonghjornu Saveriu = Salute O Savé.
Traduction: Bonjour Xavier.

- Cumu và ?
Traduction: - Comment ça va ?

- Và bè !
Traduction: - Ca va bien !

- Cumu sì ? In forma ?
Traduction: - Comment vas-tu ? En forme ?

- Pianu pianu ! = abbastanza !
Traduction: - Tout doucement ! = ça peut aller !

È ellu, qual'hè ? = Quale hè ?
Traduction: Et lui qui est-ce ?

- Hè u me zìu.
Traduction: - C'est mon oncle.

- Benvinuti !
Traduction: - Bienvenus.

- Vi presentu u mo fratellu.
Traduction: - Je vous présente mon frère.

- Enchanté !
Traduction: - Mi face piacè !

Di quale ne site ?
Traduction: De quelle famille êtes-vous ?

Sò Mauriziu Santini, u figliolu di u duttore. 
Traduction: Je suis Maurice Santini, le fils du docteur.

È voi, quale site ?
Traduction: Et vous, qui êtes-vous ?

Mi chjamu Petru.
Traduction: Je m'appelle Pierre.

Sò u cuginu di Catalina.
Traduction: Je suis le cousin de Catherine.

Vi ringraziu = à ringraziavvi.
Traduction: Je vous remercie.

- bien le bonjour à ton père !
Traduction: - Au revoir, Pierre.

- Tante salute à bàbbitu !
Traduction: - Avvèdeci, O Pé.

Bona sera.
Traduction: Bonsoir (quand on se rencontre).

À bona sera.
Traduction: Bonsoir (quand on se quitte).

À bona notte.
Traduction: Bonne nuit.

Ghjuliu hè u maritu di Marìa.
Traduction: Jules est le mari de Marie.

A so moglia hè cascata inde e scale.
Traduction: Sa femme est tombée dans les escaliers.

U mo babbu hè partutu stamane.
Traduction: Mon père est parti ce matin.

Dì à bàbbitu ch'ellu colli.
Traduction: Dis à ton père qu'il monte.

Mamma colla à u paese.
Traduction: Maman monte au village.

Chjama à Màmmata.
Traduction: Appelle ta mère.

Per e vacanze, i so genitori sò in Nizza.
Traduction: Pendant les vacances, ses parents sont à Nice.

U zitellu si ghjoca à pallò.
Traduction: L'enfant joue au ballon.

U nostru figliolu travaglia in Aiacciu.
Traduction: Notre fils travaille à Ajaccio.

O figliò, stà attentu da ùn cascà.
Traduction: O fils, fais attention de ne pas tomber !

A mo figliola hè studiente in Parigi.
Traduction: Ma fille est étudiante à Paris.

À babbone (caccaru, missiavu) li piace à manghjà u prisuttu.
Traduction: Grand-père aime manger le jambon.

Mammone hè vechja (caccara, minnanna).
Traduction: Grand-mère est vieille.

U fratellu di Luigi hà manghjatu e fràgule.
Traduction: Le frère de Louis a mangé les fraises.

Aghju una surella.
Traduction: J'ai une soeur.

Petru hà dui fratelli è trè surelle.
Traduction: Pierre a deux frères et trois soeurs.

U cunnosci u figliulinu di Marcellu ?
Traduction: Tu connais le petit-fils de Marcel ?

Paulu corre inde u pratu cù a so figliulina.
Traduction: Paul court dans le pré avec sa petite-fille.

Chjameraghju u mo cuginu.
Traduction: J'appellerai mon cousin.

A cugina di Lucìa si chjama Ànghjula.
Traduction: La cousine de Lucie s'appelle Angèle.

U mo cuginu carnale hè u figliolu di a mo zìa Ghjulia.
Traduction: Mon cousin germain est le fils de ma tante Julie.

Quessu hè u mo cuginu di terzu.
Traduction: Celui-ci est mon cousin issu de germain.

Zìu Francescu si sciacca una fetta di prisuttu.
Traduction: L'oncle François s'envoie une tranche de jambon.

Zìa Catalina hè una brava donna.
Traduction: Tante Catherine est une brave (gentille) femme.

O zì, à u frescu ? [1]
Traduction: O tante, vous prenez le frais ?

U nipote di Ghjuvanni hè malatu.
Traduction: Le neveu de Jean est malade.

A nipote di Ghjuvan Petru hè malata.
Traduction: La nièce de Jean-Pierre est malade

In quant'à mè, i nipoti di Ghjuvanni sò scemi.
Traduction: A mon avis, les neveux de Jean sont fous.

Petru hè u cugnatu di Lucìa.
Traduction: Pierre est le beau-frère de Lucie.

Lucìa hè a cugnata di Petru.
Traduction: Lucie est la belle-soeur de Pierre.

U mo sóceru m'hà imprestatu u so fucile.
Traduction: Mon beau-père m'a prêté son fusil.

A so sócera l'hà fattu un bellu pastizzu.
Traduction: Sa belle-mère lui a fait un beau gâteau.

U ghjènneru di Marcu hà persu i so spichjetti.
Traduction: Le beau-fils de Marc a perdu ses lunettes.

A to nora hè un puttachjone.
Traduction: Ta belle-fille est une vraie commère.

Piove oghje
Traduction: Aujourd'hui, il pleut

Eri, hè piossu
Traduction: Hier, il a plu

Face u caldu / fretu
Traduction: Il fait chaud / froid

Aghju u fretu
Traduction: J'ai froid

Luce u sole
Traduction: Le soleil luit

A luna luccica
Traduction: La lune brille

Stasera niverà 
Traduction: Il neigera ce soir

Ci hè a neve 
Traduction: Il y a de la neige 

Mettu l'acetu inde a insalata / l'insalata.
Je mets le vinaigre dans la salade.

Catalina hà betu un pocu d'acqua fresca.
Traduction: Catherine a bu un peu d'eau fraîche.

Dammi un pezzu di pane cù butiru.
Traduction: Donne moi un peu de pain avec du beurre.

Vulete un caffè ?
Traduction: Voulez-vous un café ?

A lumaca manghja u carbusgiu.
Traduction: L'escargot mange le chou.

A carne hè fràcica.
Traduction: La viande est pourrie.

Puzza issu casgiu !
Traduction: Ce fromage pue !

Ci hè un càvulufiore inde l'ortu.
Traduction: Il y a un chou-fleur dans le potager.

Eccu un ceciu !
Traduction: Voici un pois chiche !

Mi piàcenu i ceci.
Traduction: J'aime les pois chiches.

À mè, mi piace a cicculata.
Traduction: Moi, j'aime le chocolat.

Hè grossa a cipolla.
Traduction: L'oignon est gros.

Hè ora di cullaziò (cullazione).
Traduction: C'est l'heure du déjeuner.

Hè bona a cunfittura di chjarasge.
Traduction: La confiture de cerises est bonne.

Mamma mena a farina incù l'ove.
Traduction: Maman mélange la farine et les oeufs.

Avemu manghjatu e fasgiole.
Traduction: Nous avons mangé des chataignes bouillies.

Sò boni i fasgioli cù u prisuttu.
Traduction: Les haricots sont bons avec le jambon.

Dàtemi una fetta di pulenda.
Traduction: Donnez-moi une tranche de polenta.

U figatellu si manghja d'invernu.
Traduction: On mange le figatelli en hiver.

Fàteci una frittata cù i pomi.
Traduction: Faites-nous une omelette de pommes de terre.

U furmagliu hè caru caru.
Traduction: Le fromage est très cher.

Pigliu un ghjacciu per rinfriscammi.
Traduction: Je prends une glace pour me rafraîchir.

U granu hè siccatu di maghju.
Traduction: Le blé est coupé en mai. (céréale)

L'insalata / A insalata si manghja incù oliu d'alive.
Traduction: On mange la salade avec de l'huile d'olive.

À a ghjatta, li piace u latte !
Traduction: La chatte aime le lait !

Maghjaremu lentichje è carne.
Traduction: Nous mangerons des lentilles et de la viande.

L'ape fàcenu u mele.
Traduction: Les abeilles font du miel.

Dumènicu compra l'oliu per mette incù a/l' insalata.
Traduction: Dominique achète de l'huile pour mettre avec la salade.

A ghjallina hà fattu un ovu stamane.
Traduction: La poule a fait un oeuf ce matin.

À mè, mi basta un pezzu di pane !
Traduction: Moi, un morceau de pain me suffit !

O Dumè, sèrvimi un pastizzu !
Traduction: Dominique, sers-moi un pastis !

Mamma ci hà fattu un pastizzu.
Traduction: Maman nous a fait un gâteau.

Li faraghju un pesciu cù u risu.
Traduction: Je leur ferai un poisson avec du riz.

Ssu prisuttu hè più bonu chè l'altru.
Traduction: Ce jambon est meilleur que l'autre.

E ravanette sò belle rosse.
Traduction: Les radis sont très rouge.

Cusì bona ssa salciccia !
Traduction: Quelle est bonne cette saucisse !

U suchju di e fràule hè inzuccaratu (dolce).
Traduction: Le jus de fraises est sucré.

U zitellu manghja a suppa cù una cuchjara.
Traduction: L'enfant mange sa soupe avec une cuillère.

Ci sò dui tóruli inde l'ovu !
Traduction: Il y a deux jaunes dans l'œuf !

Biite un pocu di vinu prima d'andàssine.
Traduction: Buvez un peu de vin avant de vous en aller.

Mittite un zùccaru inde u caffè.
Traduction: Mettez un sucre dans le café.

La mer est belle.
Traduction: U mare hè bellu.

Nous partons faire un tour à la montagne.
Traduction: Partemu à facci un giru in muntagna.

Je suis monté jusqu'au lac de Créno.
Traduction: Sò cullatu sin'à u lavu di Crenu.

La forêt a été brûlée.
Traduction: A furesta hè stata brusgiata.

On peut voir un avion en plein ciel.
Traduction: À mezu celu, pudemu vede un aviò.

Il y a beaucoup de truites dans le fleuve.
Traduction: Ci sò assai truìte inde u fiume.

Les arbres sont tordus.
Traduction: L'àlburi sò storti.

L'âne chemine au milieu du sentier.
Traduction: U sumere viaghja à mezu chjassu.

On trouve des champignons dans le maquis.
Traduction: Si tròvanu funghi inde a machja.

Le pré est fleuri. Les fleurs sont blanches et bleues.
Traduction: U pratu hè fiuritu. I fiori sò bianchi è turchini. 

L'acellu face un nidu annantu à l'àrburu.
Traduction: L'oiseau fait un nid sur l'arbre.

Cacciu / caccighjeghju l'acillame chì aghju u permessu.
Traduction: Je chasse le gibier à plumes car j'ai le permis.

À Pasquale li piace di più u salvaticume.
Traduction: Pascal préfère le gibier à poils.

Mì, ci hè un àcula à mezu celu.
Traduction: Regarde, il y a un aigle en plein ciel.

U pastore porta l'agnellu feritu.
Traduction: Le berger porte l'agneau blessé.

L'ala di a farfalla hè bella.
Traduction: L'aile du papillon est belle.

L'altore manghja l'animali morti.
Traduction: Le vautour mange les animaux morts.

Aghju vistu un'ànatra.
Traduction: J'ai vu un canard.

L'anguilla si piatta sott'à e petre.
Traduction: L'anguille se cache sous les pierres.

Ci hè un animale inde a casa.
Traduction: Il y a un animal dans la maison.

L'ape fàcenu u mele.
Traduction: Les abeilles font le miel.

Puzza u beccu !
Traduction: Il pue le bouc !

A bèllula caccia / caccighjeghja i topi.
Traduction: La belette chasse les rats.

Ssa bestia hè goffa.
Traduction: Cette bête est laide.

Hà persu u so bistiame inde u focu.
Traduction: Il a perdu son bétail dans le feu.

Trà u boie è u sumere, c'era u ciucciu.
Traduction: Entre le boeuf et l'âne il y avait le bébé.

I bruchi anu manghjatu e insalate.
Traduction: Les chenilles ont mangé les salades.

Ssu camellu hè u meiu.
Traduction: Ce chameau est à moi.

Parte à a caccia cù u so cane.
Traduction: Il part à la chasse avec son chien.

Stu caniolu hè dumatu pè a caccia.
Traduction: Ce chiot est dressé pour la chasse.

A capra nera si n'hè scappata.
Traduction: La chèvre noire s'est enfuie.

U caprettu hà suttu u latte.
Traduction: Le chevreau a sucé la lait.

U cavallu galoppa ind'u pratu.
Traduction: Le cheval galope dans le pré.

Petru hà tumbatu un cignale.
Traduction: Pierre a tué un sanglier.

C'era dinò un cignalottu.
Traduction: Il y avait aussi un marcassin.

U ciocciu face un tazzu !
Traduction: Le hibou fait un de ces vacarmes !

A coda di a ghjandaghja hè bianca.
Traduction: La queue du geai est blanche.

U corbu hè neru.
Traduction: Le corbeau est noir.

U cunìgliulu hè impauritu.
Traduction: Le lapin a peur.

A cuppulata viaghja pianu pianu.
Traduction: La tortue chemine tout doucement.

A curnachja ùn si manghja micca.
Traduction: On ne mange pas la corneille.

Ci hè un falchettu chì vola.
Traduction: Il y a un épervier qui vole.

U falcu hà chjappatu un topu.
Traduction: Le faucon a attrapé un rat.

Un falcu di fiume vula sopra a casa.
Traduction: Une buse vole au dessus de la maison.

U fasgianu era annant'à a strada.
Traduction: Un faisan était sur la route.

L'àsinu manghja fenu.
Traduction: L'âne mange du foin.

In ssa gabbia ci sò dui acelli.
Traduction: Dans cette cage il y a deux oiseaux.

A ghjallina hà fattu un ovu.
Traduction: La poule a fait un oeuf.

U ghjallu canta à l'alba.
Traduction: Le coq chante à l'aube.

U ghjattu ghjoca cù una palla.
Traduction: Le chat joue avec une balle.

A ghjumenta corre inde u pratu.
Traduction: La jument court dans le pré.

U grillu salta sempre.
Traduction: Le grillon saute toujours.

A lèvura fughje davanti à u cacciadore.
Traduction: Le lièvre fuit devant le chasseur.

Santa hà vistu un lione.
Traduction: Toussainte a vu un lion.

A lovia di zìu Ghjuliu hè malata.
Traduction: La laie de l'oncle Jules est malade.

A lumaca manghja a insalata.
Traduction: L'escargot mange la salade.

U lupu hè un animale feroce.
Traduction: Le loup est un animal féroce.

L'alifante hè un mammiferu.
Traduction: L'éléphant est un mammifère.

E mosche vòlenu tutt'à l'ingiru.
Traduction: Les mouches volent tout autour.

Hà messu a legna à nant'à u mulu.
Traduction: Il a mis le bois sur le mulet.

L'orsu corre inde a machja.
Traduction: L'ours court dans le maquis.

U pastore fisca a pècura.
Traduction: Le berger siffle la brebis.

À caccia, cercu e pernice.
Traduction: A la chasse, je cherche les perdrix.

Un pesciu rossu m'hè scappatu.
Traduction: Un poisson rouge m'a échappé.

U piulellu hè giallu.
Traduction: Le poussin est jaune.

Aghju trovu una piuma d'oca.
Traduction: J'ai trouvé une plume d'oie

U porcu hè grossu.
Traduction: Le cochon est gros.

S'hè fattu punghje da un porcuspinu.
Traduction: Il s'est fait piquer par un porc-épic.

A volpe hà manghjatu u pullastru.
Traduction: Le renard a mangé le poulet.

Manghja a quagliula !
Traduction: Mange la caille !

A ranochja salta ind'u lavu.
Traduction: La grenouille saute dans le lac.

U ricciu si move ind'a so tana.
Traduction: Le hérisson se déplace dans sa tanière.

Mi stumaca ssu ruspu !
Traduction: Il me dégoûte ce crapaud !

Tamante sanne ch'ellu hà ssu cignale !
Traduction: Quels grands crocs il a ce sanglier !

U cignale l'hà data una sannata.
Traduction: Le sanglier lui a donné un coup de dents.

A scimia mi face ride.
Traduction: Le singe me fait rire.

U sumere hà l'arechje grande.
Traduction: L'âne a de grandes oreilles.

Cum'ella hè chjuca a talpa !
Traduction: Comme elle est petite la taupe !

U topu hà una coda longa.
Traduction: Le rat a une longue queue.

U topupinnutu hè appesu à u cantellu.
Traduction: La chauve-souris est suspendue à la poutre.

Aghju mancatu u tòrdulu.
Traduction: J'ai manqué la grive.

U toru mi corre appressu.
Traduction: Le taureau me court après.

A truìta si manghja bella cotta.
Traduction: On mange la truite bien cuite.

U tupucciu teme u frastornu.
Traduction: La souris craint le vacarme.

A vacca hà fattu assai latte.
Traduction: La vache a fait beaucoup de lait.

Mettu un varmu à l'amu per piscà i pesci.
Traduction: Je mets un ver à l'hameçon pour pêcher les poissons.

A vespa hà puntu à Luigi à u bracciu.
Traduction: La guêpe a piqué Louis au bras.

U vitellu seguita a vacca.
Traduction: Le veau suit la vache.

A volpe hè maligna.
Traduction: Le renard est malin.

A zinzala m'hà puntu.
Traduction: Le moustique m'a piqué.

"""


model = ChatOpenAI(model="gpt-4o", temperature=0, api_key="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")

prompt = ChatPromptTemplate.from_messages(
    [
        ("system", tutor_prompt_template),
        ("assistant", WELCOME_MESSAGE),
        MessagesPlaceholder(variable_name="chat_history"),
        ("user", "{username}: {input}"),
    ]
)
parser = StrOutputParser()
chain = prompt | model | parser

async def main():
    driver = AsyncDriver(
        {
            "token": "yuethjyj9jraznw5fxkcchcbxy",
            "url": "agora.parolla.chat",
            "port": 443,
            "request_timeout": 3000,
            "scheme": "https",
            "debug": True,
        }
    )
    await driver.login()

    async def compute_history(posts, user_id):
        history_messages = []
        for post_id in posts["order"]:
            p = posts["posts"][post_id]
            
            username = await driver.users.get_user(user_id=p["user_id"])
            history_messages.append(("user" if p["user_id"] == user_id else "assistant", f"{username['username']}: {p["message"]}\n\n"))
        return list(reversed(history_messages))

    async def handle_message(post, **kwargs):
        print(post, kwargs)
        response = json.loads(post)
        if "event" not in response:
            return
        event_type = response["event"]
        if event_type != "posted":
            return
        raw_data = response["data"]["post"]
        raw_data_dict = json.loads(raw_data)
        user_id = raw_data_dict["user_id"]
        root_id = (
            raw_data_dict["root_id"]
            if raw_data_dict["root_id"]
            else raw_data_dict["id"]
        )
        channel_id = raw_data_dict["channel_id"]
        if channel_id != "tp1eg6uitfy19cugrju5uut1wy" and channel_id != "8ji456qzh3fyzcu5buoismaxjh":
            return
        sender_name = response["data"]["sender_name"]
        raw_message = raw_data_dict["message"]

        if "parollatest" in sender_name.lower():
            return
        posts = await driver.posts.get_posts_for_channel(channel_id=channel_id)
        chat_history = await compute_history(posts, user_id)

        response = chain.invoke({
            "chat_history": chat_history,
            "input": raw_data,
            "username": sender_name
        })
        
        response = response.replace("parollatest: ", "").replace("parollatest:", "").replace("parollatest", "")
        await driver.posts.create_post(
            options={
                "channel_id": channel_id,
                "message": response,
            }
        )

    await driver.init_websocket(handle_message)


asyncio.run(main())
